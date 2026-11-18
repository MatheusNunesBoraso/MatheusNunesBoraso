#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Busca dados do GitHub (GraphQL) e grava data/contributions.json.
Token: env GH_TOKEN ou GITHUB_TOKEN. Login: env GH_LOGIN (default MatheusNunesBoraso).
Repos em destaque: lista FEATURED abaixo; o que não existir é ignorado,
e o restante é completado pelos mais estrelados com descrição."""
import json, os, sys, urllib.request, datetime

LOGIN = os.environ.get("GH_LOGIN", "MatheusNunesBoraso")
TOKEN = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
FEATURED = ["claude-code-status-line", "nucleo-escolar-2.0",
            "vintagestory-automacao", "husky-commitlint-translate"]
MAX_FEATURED = 4
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "data", "contributions.json")

QUERY = """
query($login:String!){
  user(login:$login){
    name login bio avatarUrl
    followers{totalCount} following{totalCount}
    contributionsCollection{
      contributionCalendar{
        totalContributions
        weeks{ contributionDays{ date weekday contributionCount } }
      }
    }
    repositories(first:100, ownerAffiliations:OWNER, privacy:PUBLIC,
                 orderBy:{field:STARGAZERS, direction:DESC}){
      totalCount
      nodes{ name description stargazerCount forkCount isFork
             primaryLanguage{name color} pushedAt }
    }
  }
}"""

def gql(query, variables):
    if not TOKEN:
        sys.exit("Faltou GH_TOKEN/GITHUB_TOKEN no ambiente.")
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body,
        headers={"Authorization": "bearer " + TOKEN,
                 "Content-Type": "application/json",
                 "User-Agent": "profile-cards"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.load(r)
    if "errors" in out:
        sys.exit("GraphQL: " + json.dumps(out["errors"]))
    return out["data"]

def pick_featured(nodes):
    by_name = {n["name"]: n for n in nodes}
    chosen, seen = [], set()
    for name in FEATURED:
        n = by_name.get(name)
        if n and name not in seen:
            chosen.append(n); seen.add(name)
    for n in nodes:  # completa com estrelados que tenham descrição
        if len(chosen) >= MAX_FEATURED:
            break
        if n["name"] in seen or n["isFork"] or not n.get("description"):
            continue
        chosen.append(n); seen.add(n["name"])
    out = []
    for n in chosen[:MAX_FEATURED]:
        lang = n.get("primaryLanguage") or {}
        out.append({"name": n["name"],
                    "description": (n.get("description") or "")[:110],
                    "stars": n["stargazerCount"], "forks": n["forkCount"],
                    "language": lang.get("name"), "langColor": lang.get("color")})
    return out

def main():
    u = gql(QUERY, {"login": LOGIN})["user"]
    cal = u["contributionsCollection"]["contributionCalendar"]
    data = {
        "generatedAt": datetime.datetime.utcnow().isoformat() + "Z",
        "profile": {"name": u["name"], "login": u["login"], "bio": u["bio"],
                    "avatarUrl": u["avatarUrl"],
                    "followers": u["followers"]["totalCount"],
                    "following": u["following"]["totalCount"],
                    "publicRepos": u["repositories"]["totalCount"]},
        "calendar": {"totalContributions": cal["totalContributions"],
                     "weeks": cal["weeks"]},
        "featured": pick_featured(u["repositories"]["nodes"]),
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("ok ->", OUT, "| contrib:", cal["totalContributions"],
          "| featured:", [r["name"] for r in data["featured"]])

if __name__ == "__main__":
    main()
