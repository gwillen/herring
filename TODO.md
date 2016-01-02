## Models
Field for link to actual puzzle page

## Views
X Load basic template
X Embed initial data into page load as JSON for React to use
X RESTful endpoints for updates/changes: write them, make React use them

## Templates:
X Just one dynamic page
X /admins is sane
Static pages for puzzle-solving resources and team info, if any

(Do we want a `teams` app for team info/whitelabeling/etc? Doesn't *really* make sense, unless team leaders are scared of editing HTML.)

## React app:
X Update answer to puzzle
X Update notes on puzzle
X Update tags on puzzle
X Make not laggy / update optimistically / something
Update link associated with puzzle
X Filter by has_answer
X Filter by tag

## Other
Account generation/login/auth
  * People can create accounts (oauth?)
  X People must login to see website
  X Can log out via menu
  * Accounts created by admin?
  * People have their accounts be approved by admin in admin interface in order to see website?
Link generation for puzzles --> GDocs/Etherpad
X Announcement for correct answers
Ability to make other announcements
Chat integration
Add list of admin users to /admin login page to make it useful for nonadmins who want to know who to bother

## Wishlist
Automagic tracking of who is working on what.
User profiles with contact information and a photo.
