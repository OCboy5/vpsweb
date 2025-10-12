# WeChat Article Generation & Publishing Expansion for vpsweb

## Core Features

- Generate WeChat-formatted article from translation JSON

- Create concise translation notes

- Assign local cover image

- Publish to WeChat Official Account Drafts

- Two new CLI commands

- Enhanced metadata in translate workflow

## Tech Stack

{
  "Web": {
    "arch": null,
    "component": null
  },
  "iOS": null,
  "Android": null
}

## Design

WeChat-rich-text HTML: professional, clean typography, clear sectioning, minimal inline styles; readable original poem, polished translation, concise notes, and a small copyright disclaimer.

## Plan

Note: 

- [ ] is holding
- [/] is doing
- [X] is done

---

[X] Analysis & proposal

[ ] Article rendering from translation JSON: title, original poem, final translation, elegant HTML, copyright disclaimer

[ ] Automatic “translation notes” creation by summarizing decisions across initial/revised notes and editor suggestions

[ ] Cover image assignment: accept local image, validate, associate for article

[ ] Image handling: upload cover and inline images to WeChat, replace URLs in content

[ ] Publish to WeChat Drafts: create draft with title, author, digest, content, thumb_media_id

[ ] CLI commands: vpsweb generate-article and vpsweb publish-article with flags (input, cover, digest, author, dry-run)

[ ] Metadata enhancements in translate workflow: poem_title, poet_name, series index, digest, slug, suggested publish date

[ ] Safety and pacing: credentials management, rate-limit awareness, 1/day scheduling guidance
