# Mystery Game Sites: Simple Guide

This guide explains how to add game files and publish the websites using GitHub. You do not need to edit the Python code.

## Before you start

There are two GitHub repositories:

- **Game content repository:** private repository containing the `games` folder. Add PDFs and media here.
- **Game publisher repository:** this repository. Use its **Actions** tab to build and publish the websites.

Adding files to the content repository does not publish the website immediately. After saving your changes there, run the **Publish** workflow in the publisher repository.

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

## Add a YouTube video to a game page

The small text file connects the YouTube video to a PDF page. Its filename must match the PDF exactly, except for the `.txt` ending.

1. From the game content repository home page, create the media folder by choosing **Add file → Create new file** and entering:

   `games/dead-weight-mini-mystery/media/README.txt`

   Type a short note and select **Commit changes**. If you are already inside the game folder, you can instead create `media/README.txt` there.

2. Open the new `media` folder. Choose **Add file → Create new file** and enter a text filename matching the PDF. For `010_Case_Introduction.pdf`, use:

   `010_Case_Introduction.txt`

3. In that file, add the YouTube link like this, then select **Commit changes**:

   `youtube=https://youtu.be/VIDEO_ID`

   Replace the example link with the video’s share link, then commit the file. The video will appear on that game page when you publish.

You can put `youtube=https://www.youtube.com/watch?v=VIDEO_ID` instead if that is the link You copied from YouTube. The file name still has to match the PDF.

## Publish the game websites

Publish after adding or changing game files. The workflow reads the latest committed files from the `main` branch of the private game content repository.

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

On the monitoring dashboard, use **Add new team** to give another team its own name and station order. Assign a station when the team is ready for it, then mark it complete when they report back. The dashboard shows completed, current, and next stations. Share a station link by email or use **Copy link**.

Team names and progress are saved in the browser's local storage. Keep using the same browser and device during the game; clearing browser data or switching devices will not carry the saved progress across.

Station links open one page without the game's menu or previous/next controls. The site is public static hosting, so a station link does not prevent someone from manually opening another public game URL. Do not use it to protect confidential material.
