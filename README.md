# Mystery Game Sites: Simple Guide

This guide explains how to add game files and publish the websites using GitHub. You do not need to edit the Python code.

## Before you start

There are two GitHub repositories:

- **Game content repository:** private repository containing the `games` folder. Add PDFs and media here.
- **Game publisher repository:** this repository. Use its **Actions** tab to build and publish the websites.

Adding files to the content repository does not publish the website immediately. After saving your changes there, run the **Publish** workflow in the publisher repository.

## Choose which games are public

The workflow publishes only the game folders named in `published-games.txt`. The file is already included in the publisher setup. It must be at the top level of the private game content repository, beside the `games` folder. Do not create another copy. A folder not named in this list stays out of the public website.

To choose which games are public, open the existing `published-games.txt` in the private game content repository and select **Edit**. Put the exact folder name of each game you want online on its own line, then select **Commit changes**. For example:

```text
# One exact folder name per line
dead-weight-mini-mystery
```

Copy each name exactly as its game folder appears inside `games`. Blank lines and lines starting with `#` are ignored. The publish workflow will stop with an error if the file is missing, empty, or names a folder that does not exist; this prevents accidentally publishing every game folder.

## Add a new game

1. Open the home page of the private **game content repository** on GitHub. Start at the repository home page so the paths below begin with `games/`.
2. Create a folder for the game. Choose **Add file → Create new file** and enter a path such as:

   `games/dead-weight-mini-mystery/title.txt`

   Type the game’s display name into the file, then select **Commit changes** to save it. The folder name becomes part of the website address; use simple words separated by hyphens.

3. Create the PDFs folder by choosing **Add file → Create new file** again and entering:

   `games/dead-weight-mini-mystery/pdfs/README.txt`

   Add a short note and select **Commit changes**. This creates the folder. You can leave the small `README.txt` there.

4. Open the new `pdfs` folder. Choose **Add file → Upload files**, select the game PDFs, and select **Commit changes** to save the upload.

5. Give each PDF a three-digit number at the start of its filename, followed by an underscore and a short name. For example:

   - `010_Case_Introduction.pdf`
   - `020_Clue_One.pdf`
   - `030_Final_Clue.pdf`

   The numbers set the order on the self-run game site. A multi-page PDF appears as one game section.

Creating a new game folder does not make it public. To publish it, edit the existing `published-games.txt`, add its exact folder name on a new line, commit the change, then run **Publish**. To take just one game offline, edit the same file, remove that game's line, and run **Publish** again. Other listed games stay online. The **Unpublish** action takes all games offline.

## Add a YouTube link to a game page

Add a numbered `.txt` file in the game's `media` folder and put the YouTube link in it. The website will display the video on that game page.

1. In the private game content repository, open the game's folder and choose **Add file → Create new file**. Enter `media/005_Case_Introduction.txt` as the filename. If the `media` folder does not exist yet, GitHub creates it as part of this step.
2. In the file, add the YouTube link in this format:

   `youtube=https://youtu.be/VIDEO_ID`

   Replace the example URL with the video's share link. You can also use a link like `youtube=https://www.youtube.com/watch?v=VIDEO_ID`.

3. Select **Commit changes**, then run the **Publish** workflow in the game publisher repository.

The three-digit number controls where the page appears in the game. For example, `005_` puts the video page before `010_` pages. To show a video on a page that already has a PDF, use the same number and name as the PDF. For `010_Case_Introduction.pdf`, name the text file `010_Case_Introduction.txt`.

For a video-only page, do not keep a matching PDF in the game's `pdfs` folder. If changing an existing page to video-only, remove its PDF or move it outside the game folder.

## Add an emoji feedback question to a station

Create a text file in the game's `surveys` folder. Use the same filename stem as the PDF or station page. For example, for `pdfs/010_Case_Introduction.pdf`, create `surveys/010_Case_Introduction.txt` with:

```text
question=How did your team find this clue?
options=😞|Difficult;😐|Okay;🙂|Good;🤩|Excellent
```

The `question=` line is required. The `options=` line is optional; if you leave it out, the site uses four default emoji choices. The question appears on that station page. The team's answer is saved when they select an emoji and click **Done**.

## Connect the dashboard to Google Sheets

This one-time setup lets the host see team progress and survey answers from other devices and email a summary when the game ends.

1. Create a Google Sheet for game responses. Copy the ID from its web address (the part between `/d/` and `/edit`).
2. Open the `apps-script/Code.gs` file in this repository, copy its contents, and create a project at [script.google.com](https://script.google.com). Paste the code into `Code.gs`.
3. In the Apps Script project, open **Project Settings** and add these **Script Properties**: `SPREADSHEET_ID` (the Sheet ID), `HOST_EMAIL` (where summaries should be sent), and `HOST_PIN` (a private PIN the host enters before sending a summary).
4. Return to the script editor, choose `setupMysterySheets` from the function menu, and click **Run** once. Then run `authorizeMysteryEmail` once. Approve Google's access prompts. The first function creates the tabs used to store teams and responses; the second authorizes the email feature.
5. Choose **Deploy → New deployment → Web app**. Set **Execute as** to your account and allow access to **Anyone**. Deploy, then copy the web app URL ending in `/exec`.
6. In the **game publisher repository**, open **Settings → Secrets and variables → Actions → Variables**. Add a repository variable named `APPS_SCRIPT_URL` and paste the web app URL as its value.
7. Run the **Publish** workflow again. The generated station pages and host dashboard will now use Google Sheets.

Keep the host PIN private. The host dashboard asks for it when sending the email summary. Each game session's dashboard link contains a unique session key; keep that link with the organizer. Apps Script source is stored in this repository for future maintainers, but its live deployment is managed in Google Apps Script.

## Publish the game websites

Publish after adding or changing game files or the published-games list. The workflow reads the latest committed files from the `main` branch of the private game content repository and includes only the game folders listed in `published-games.txt`.

1. Open the **game publisher repository** on GitHub.
2. Select **Actions**.
3. Select **Publish mystery game site and host dashboard** from the workflow list.
4. Select **Run workflow**.
5. In the **action** menu, choose **publish**.
6. Select **Run workflow** again and wait for the run to finish successfully.
7. Open the completed run. Its summary shows the full game website and the host dashboard links.

The host hub is at `<your GitHub Pages address>/host/`. It includes a full self-run game link and a host dashboard link for each game.

## Unpublish the websites

Unpublishing takes **all games** offline from the public site. It does not delete the PDFs or other files in the private game content repository.

1. In the **game publisher repository**, select **Actions**.
2. Select **Publish mystery game site and host dashboard**.
3. Select **Run workflow**.
4. In the **action** menu, choose **unpublish**.
5. Select **Run workflow** again and wait for it to finish.

The public address will show an unavailable notice. To make the games public again, run the workflow with **publish** selected.

## Hybrid and in-person games

From the host hub, open a game's host dashboard. Name the first team and click stations in that team's visit order. **Initiate game** saves the team and station order in the browser and opens the monitoring dashboard in a new tab.

On the monitoring dashboard, use **Add new team** to give another team its own name and station order. Assign a station when the team is ready for it, then share the link using **Copy link** or email. When players select feedback and click **Done**, their progress and answer appear in the host dashboard. The dashboard checks for updates every five seconds. At the end, choose **Email survey responses** and enter the host PIN to email the team responses.

The browser keeps a local copy of the setup. With Google Sheets connected, team progress and responses are also stored online, so the host dashboard can refresh them across devices. Without the Apps Script URL configured, progress stays in that browser and cannot receive players' updates from another device.

Station links open one page without the game's menu or previous/next controls. The site is public static hosting, so a station link does not prevent someone from manually opening another public game URL. Do not use it to protect confidential material.
