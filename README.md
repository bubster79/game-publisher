# game-publisher

This repository builds the public static mystery-game website from the private
game-content repository. The existing game pages remain available for
self-run games, with their page menu and previous/next navigation.

## Hybrid and in-person games

When the publish workflow finishes, open the game hub at
`<GitHub Pages URL>/host/`. Each game card includes links to both the complete
self-run game and its host dashboard. In the host setup page, name the first
team and click stations in the order teams should visit them. The selected
order is numbered on screen. **Initiate game** saves the flow and first team
in the host browser, then opens the monitoring dashboard in a new tab. The
setup page stays open, and the full self-run game also opens in a new tab.

The monitoring dashboard lists each team's completed sites, current site, and
next site. Add more named teams or delete a team from this dashboard; each
team has its own progress through the shared game flow. Click **Assign next
station** to create the team's current station link, then share it by text
message, email, WhatsApp, or copy/paste. When the team reports back, mark the
current site complete to enable its next station. Completed sites are crossed
out in the team's history.

The dashboard keeps the game flow, team count, current assignments, and
completion history in the browser's local storage. Keep the host dashboard in
the same browser and on the same device throughout the game. Clearing browser
data or switching devices clears or separates this saved progress.

Station URLs open a standalone copy of one game page, without the game menu or
previous/next controls. GitHub Pages is static hosting, so these URLs do not
authenticate players or prevent someone from manually opening another public
URL. Use the station links to control normal player navigation, not to protect
confidential content.

The workflow publishes the game hub at `/host/`, a setup page per game at
`/host/<game-slug>/`, and its monitoring page at
`/host/<game-slug>/monitor.html`. Team station pages are generated under
`/stations/<game-slug>/<page-slug>/`.
