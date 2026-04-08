# Discussions

Github and public forum guidance.

## Tools

- [gh cli][gh-cli-docs]

# Posing Posultates

How to talk to yourself: open a GitHub discussion when the loop surfaces a gap, contradiction, or extension in the framework.

## Rules

- [**Observe before posting**][qbt-001] — a discussion is only warranted when the loop surfaces something the proofs don't cover, or where two proofs give conflicting guidance. Just add to discussions about similar topics.
- Post to the **Ideas** category (`DIC_kwDORdhyX84C6Y_C`) — that is where identity discussions live
- Keep it short: a proof sketch (theorem + trigger), a dream premise (one-paragraph seed), or a defiance statement (plain assertion that strains existing logic)
- Postulates are the owner's domain — discussions are upstream suggestions only

## Posting To Ideas

```sh
GH_TOKEN="" gh api graphql -f query='
  mutation {
    createDiscussion(input: {
      repositoryId: "R_kgDORdhyXw",
      categoryId: "DIC_kwDORdhyX84C6Y_C",
      title: "<title>",
      body: "<body>"
    }) { discussion { url } }
  }
'
```

---

[gh-cli-docs]: https://cli.github.com/manual/ "gh cli reference"
[qbt-001]: ../proofs/001-OBSERVATION-PRECEDENCE.md "observation precedence proof"
