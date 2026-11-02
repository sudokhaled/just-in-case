#!/usr/bin/env python3
"""Lock the GitHub repository so nobody can change main or publish without the owner.

    python3 tools/repo_guard.py apply   # set every protection (needs `gh auth login` as the owner)
    python3 tools/repo_guard.py check   # read them all back from GitHub; exits 1 if anything is wrong

What apply sets:

- main: nobody, not even the owner, can force-push or delete it.
- main: everyone except repository admins must open a pull request that passes
  the "build" check and is approved by a code owner (.github/CODEOWNERS).
- v* tags, which publish releases: only admins can create, move or delete them.
- The release workflow waits for the owner's approval (environment "release"),
  and the website deploys only from main (environment "github-pages").
- Actions: the token is read-only unless a workflow asks for more, workflows
  cannot approve pull requests, only GitHub's own actions and the third-party
  actions our workflows use may run, and every pull request from outside
  contributors needs approval before its workflows run.
- Private vulnerability reporting (SECURITY.md links to it).

Uses the GitHub CLI (gh) and the Python standard library only.
"""

import argparse
import base64
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
ADMIN_ROLE = 5  # the base "admin" repository role in rulesets (maintain = 2, write = 4)
GITHUB_OWNERS = ("actions", "github")  # covered by "allow actions created by GitHub"
RELEASE_TAGS = "v*"
USES_RE = re.compile(r"^\s*(?:-\s+)?uses:\s*([^\s#]+)", re.M)


class GuardError(Exception):
    pass


def gh(path, method="GET", body=None, missing_ok=False):
    """Call the GitHub API through the gh CLI. Returns parsed JSON, or None for 404 when missing_ok."""
    cmd = ["gh", "api", "-X", method, "-H", "X-GitHub-Api-Version: 2022-11-28", path]
    if body is not None:
        cmd += ["--input", "-"]
    try:
        r = subprocess.run(cmd, input=json.dumps(body) if body is not None else None,
                           capture_output=True, text=True)
    except FileNotFoundError:
        raise GuardError("the GitHub CLI (gh) is not installed: https://cli.github.com/")
    if r.returncode != 0:
        if missing_ok and "HTTP 404" in r.stderr:
            return None
        raise GuardError("%s %s failed: %s %s" % (method, path, r.stderr.strip(), r.stdout.strip()[:300]))
    return json.loads(r.stdout) if r.stdout.strip() else None


# ---- What the workflows need -------------------------------------------------

def workflow_problems(text):
    """Ways a workflow file could let someone change the repository or publish."""
    problems = []
    if re.search(r"\b(pull_request_target|workflow_run)\b", text):
        problems.append("uses pull_request_target or workflow_run, which run untrusted code with write access")
    if not re.search(r"^permissions:", text, re.M):
        problems.append("has no top-level permissions block, so it gets the repository default")
    for ref in USES_RE.findall(text):
        action, _, version = ref.partition("@")
        if action.startswith(("./", "docker://")) or action.split("/")[0] in GITHUB_OWNERS:
            continue
        if not re.fullmatch(r"[0-9a-f]{40}", version):
            problems.append("third-party action %s is not pinned to a full commit" % ref)
    if re.search(r"^\s*contents:\s*write", text, re.M) and not re.search(r"^\s*environment:\s*release\s*$", text, re.M):
        problems.append("can write to the repository without waiting for the owner (environment: release)")
    return problems


def third_party_patterns(texts):
    """Allow-list entries for the non-GitHub actions the workflows use, like owner/action@*."""
    found = set()
    for text in texts:
        for ref in USES_RE.findall(text):
            action = ref.partition("@")[0]
            if not action.startswith(("./", "docker://")) and action.split("/")[0] not in GITHUB_OWNERS:
                found.add(action + "@*")
    return sorted(found)


# ---- The protections ----------------------------------------------------------

def rulesets(build_app_id=None):
    check = {"context": "build"}
    if build_app_id:
        check["integration_id"] = build_app_id  # only GitHub Actions can satisfy the check
    admins = [{"actor_id": ADMIN_ROLE, "actor_type": "RepositoryRole", "bypass_mode": "always"}]
    main = {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}
    return [
        {"name": "main: keep history", "target": "branch", "enforcement": "active", "bypass_actors": [],
         "conditions": main, "rules": [{"type": "deletion"}, {"type": "non_fast_forward"}]},
        {"name": "main: changes need the owner's approval", "target": "branch", "enforcement": "active",
         "bypass_actors": admins, "conditions": main,
         "rules": [{"type": "pull_request", "parameters": {
                       "required_approving_review_count": 1, "require_code_owner_review": True,
                       "dismiss_stale_reviews_on_push": True, "require_last_push_approval": True,
                       "required_review_thread_resolution": False}},
                   {"type": "required_status_checks", "parameters": {
                       "strict_required_status_checks_policy": False, "required_status_checks": [check]}}]},
        {"name": "release tags: owner only", "target": "tag", "enforcement": "active", "bypass_actors": admins,
         "conditions": {"ref_name": {"include": ["refs/tags/" + RELEASE_TAGS], "exclude": []}},
         "rules": [{"type": "creation"}, {"type": "update", "parameters": {"update_allows_fetch_and_merge": False}},
                   {"type": "deletion"}]},
    ]


def set_environment(repo, name, reviewers, policy_name, policy_type):
    """Allow deployments to an environment only from one branch or tag pattern."""
    gh("repos/%s/environments/%s" % (repo, name), "PUT", {
        "wait_timer": 0, "prevent_self_review": False, "reviewers": reviewers,
        "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}})
    path = "repos/%s/environments/%s/deployment-branch-policies" % (repo, name)
    have = False
    for p in gh(path)["branch_policies"]:
        if p["name"] == policy_name and p.get("type", "branch") == policy_type:
            have = True
        else:
            gh("%s/%d" % (path, p["id"]), "DELETE")
    if not have:
        gh(path, "POST", {"name": policy_name, "type": policy_type})


def workflow_texts_on_github(repo, branch):
    texts = {}
    for f in gh("repos/%s/contents/.github/workflows?ref=%s" % (repo, branch)) or []:
        if f["name"].endswith((".yml", ".yaml")):
            blob = gh("repos/%s/contents/%s?ref=%s" % (repo, f["path"], branch))
            texts[f["name"]] = base64.b64decode(blob["content"]).decode("utf-8")
    return texts


def context():
    me = gh("user")
    repo = subprocess.run(["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                          capture_output=True, text=True).stdout.strip()
    if not repo:
        raise GuardError("no GitHub repository found for this folder: push it first (see .github/MAINTAINING.md)")
    info = gh("repos/" + repo)
    if info["owner"]["login"] != me["login"]:
        raise GuardError("you are signed in as %s, but %s belongs to %s" % (me["login"], repo, info["owner"]["login"]))
    return me, repo, info


def apply():
    me, repo, info = context()
    branch = info["default_branch"]
    print("Protecting %s as %s" % (repo, me["login"]))

    app_id = (gh("apps/github-actions", missing_ok=True) or {}).get("id")  # public, so no Checks permission needed
    existing = {r["name"]: r["id"] for r in gh("repos/%s/rulesets" % repo) or []}
    for rs in rulesets(app_id):
        if rs["name"] in existing:
            gh("repos/%s/rulesets/%d" % (repo, existing[rs["name"]]), "PUT", rs)
        else:
            gh("repos/%s/rulesets" % repo, "POST", rs)
        print("  ruleset: " + rs["name"])

    texts = [p.read_text(encoding="utf-8") for p in sorted(WORKFLOWS.glob("*.yml"))]
    gh("repos/%s/actions/permissions" % repo, "PUT", {"enabled": True, "allowed_actions": "selected"})
    gh("repos/%s/actions/permissions/selected-actions" % repo, "PUT", {
        "github_owned_allowed": True, "verified_allowed": False, "patterns_allowed": third_party_patterns(texts)})
    gh("repos/%s/actions/permissions/workflow" % repo, "PUT", {
        "default_workflow_permissions": "read", "can_approve_pull_request_reviews": False})
    gh("repos/%s/actions/permissions/fork-pr-contributor-approval" % repo, "PUT",
       {"approval_policy": "all_external_contributors"})
    print("  actions: read-only token, allowed actions only, outside pull requests need approval")

    set_environment(repo, "release", [{"type": "User", "id": me["id"]}], RELEASE_TAGS, "tag")
    print("  environment release: waits for %s, only from %s tags" % (me["login"], RELEASE_TAGS))
    if gh("repos/%s/environments/github-pages" % repo, missing_ok=True):
        set_environment(repo, "github-pages", [], branch, "branch")
        print("  environment github-pages: deploys only from " + branch)
    else:
        print("  environment github-pages: not created yet (turn on Pages first, then run apply again)")

    gh("repos/%s/private-vulnerability-reporting" % repo, "PUT")
    print("  private vulnerability reporting: on")
    print("\nNow run: python3 tools/repo_guard.py check")


# ---- Checks -------------------------------------------------------------------

def check():
    me, repo, info = context()
    branch = info["default_branch"]
    results = []

    def report(ok, label, detail=""):
        results.append(ok)
        print("%s  %s%s" % ({True: "PASS", False: "FAIL", None: "WARN"}[ok], label, (": " + detail) if detail else ""))

    print("Checking %s as %s\n" % (repo, me["login"]))

    # Who can write
    twofa = me.get("two_factor_authentication")
    report(None if twofa is None else bool(twofa), "Two-factor sign-in on your account",
           {True: "on", False: "OFF: turn it on at https://github.com/settings/security",
            None: "cannot read it with this login; confirm at https://github.com/settings/security"}[twofa])
    people = gh("repos/%s/collaborators?affiliation=all&per_page=100" % repo)
    writers = [p["login"] for p in people if p["permissions"].get("push") and p["login"] != me["login"]]
    report(not writers, "Only you can write to the repository", ", ".join(writers) or "no other collaborators")
    invites = gh("repos/%s/invitations" % repo)
    report(not invites, "No pending collaborator invitations", ", ".join(i["invitee"]["login"] for i in invites))
    keys = gh("repos/%s/keys" % repo)
    report(not any(not k["read_only"] for k in keys), "No deploy keys that can write",
           ", ".join(k["title"] for k in keys) or "none")
    hooks = gh("repos/%s/hooks" % repo)
    report(None if hooks else True, "No webhooks", ", ".join(h["config"].get("url", "?") for h in hooks) or "none")
    report(branch == "main", "Default branch is main", branch)

    # Rulesets, as GitHub itself applies them to main
    active = {r["type"]: r.get("parameters", {}) for r in gh("repos/%s/rules/branches/%s" % (repo, branch))}
    report("non_fast_forward" in active and "deletion" in active, "Force-push and deletion of main are blocked")
    pr = active.get("pull_request", {})
    report(pr.get("required_approving_review_count", 0) >= 1 and pr.get("require_code_owner_review", False),
           "Changes to main need an approved pull request (code owner review)")
    checks = [c["context"] for c in active.get("required_status_checks", {}).get("required_status_checks", [])]
    report("build" in checks, "Pull requests must pass the build check", ", ".join(checks) or "none")

    details = [gh("repos/%s/rulesets/%d" % (repo, r["id"])) for r in gh("repos/%s/rulesets" % repo)]
    admin_only = {(ADMIN_ROLE, "RepositoryRole")}
    for rs in details:
        actors = {(a.get("actor_id"), a["actor_type"]) for a in rs.get("bypass_actors", [])}
        rules = {r["type"] for r in rs.get("rules", [])}
        if {"deletion", "non_fast_forward"} <= rules and rs["target"] == "branch":
            report(rs["enforcement"] == "active" and not actors,
                   "Nobody can bypass the history rule", "%s (%s)" % (rs["name"], rs["enforcement"]))
        elif rs["target"] == "branch":
            report(rs["enforcement"] == "active" and actors <= admin_only,
                   "Only admins can skip the review rule", "%s (%s)" % (rs["name"], rs["enforcement"]))
    tag_rules = [rs for rs in details if rs["target"] == "tag" and rs["enforcement"] == "active"
                 and "refs/tags/" + RELEASE_TAGS in rs["conditions"]["ref_name"]["include"]]
    report(any({"creation", "update", "deletion"} <= {r["type"] for r in rs["rules"]}
               and {(a.get("actor_id"), a["actor_type"]) for a in rs.get("bypass_actors", [])} <= admin_only
               for rs in tag_rules), "Only admins can create, move or delete release tags (%s)" % RELEASE_TAGS)

    # Publishing
    env = gh("repos/%s/environments/release" % repo, missing_ok=True) or {}
    approvers = [r["reviewer"]["login"] for rule in env.get("protection_rules", [])
                 if rule["type"] == "required_reviewers" for r in rule["reviewers"]]
    report(approvers == [me["login"]], "Releases wait for your approval", ", ".join(approvers) or "no approvers")
    for name, want in (("release", (RELEASE_TAGS, "tag")), ("github-pages", (branch, "branch"))):
        policies = gh("repos/%s/environments/%s/deployment-branch-policies" % (repo, name), missing_ok=True)
        got = [(p["name"], p.get("type", "branch")) for p in (policies or {}).get("branch_policies", [])]
        report(got == [want], "%s deploys only from %s %s" % (name, want[1], want[0]),
               ", ".join("%s %s" % (t, n) for n, t in got) or "no restriction")
    pages = gh("repos/%s/pages" % repo, missing_ok=True) or {}
    report(pages.get("build_type") == "workflow", "Website is built only by the Website workflow",
           pages.get("build_type") or "Pages is not turned on")

    # Actions
    perms = gh("repos/%s/actions/permissions/workflow" % repo)
    report(perms["default_workflow_permissions"] == "read" and not perms["can_approve_pull_request_reviews"],
           "Workflow token is read-only by default and cannot approve pull requests")
    texts = workflow_texts_on_github(repo, branch)
    allowed = gh("repos/%s/actions/permissions" % repo)
    selected = gh("repos/%s/actions/permissions/selected-actions" % repo, missing_ok=True) or {}
    needed = third_party_patterns(texts.values())
    report(allowed["allowed_actions"] == "selected" and selected.get("github_owned_allowed")
           and not selected.get("verified_allowed") and set(selected.get("patterns_allowed", [])) == set(needed),
           "Only GitHub's actions and our pinned ones may run", ", ".join(selected.get("patterns_allowed", [])))
    fork = gh("repos/%s/actions/permissions/fork-pr-contributor-approval" % repo)
    report(fork["approval_policy"] == "all_external_contributors",
           "Outside contributors' pull requests need approval to run workflows", fork["approval_policy"])
    for name, text in sorted(texts.items()):
        problems = workflow_problems(text)
        report(not problems, "Workflow %s is safe" % name, "; ".join(problems))

    owners = gh("repos/%s/codeowners/errors?ref=%s" % (repo, branch), missing_ok=True)
    report(owners is not None and not owners["errors"], "CODEOWNERS is valid",
           "missing" if owners is None else "; ".join(e["message"] for e in owners["errors"]))
    pvr = gh("repos/%s/private-vulnerability-reporting" % repo)
    report(pvr.get("enabled") is True, "Private vulnerability reporting is on")

    failed = results.count(False)
    print("\n%d passed, %d failed, %d to look at" % (results.count(True), failed, results.count(None)))
    return 1 if failed else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("action", choices=("apply", "check"))
    args = ap.parse_args(argv)
    try:
        if args.action == "apply":
            apply()
            return 0
        return check()
    except GuardError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
