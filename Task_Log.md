# Team Tasks

| ID | Task Description | Deadline | Thao | Sijun | Mahir|
|---|---|---|---|---|---|
| 1 | Initial setup for backend, frondend and database| 25/09/2026 | V | ||
| 2 | Bugs and feature enhancement | 04/10/2026 | V |V ||
| 3 |Fix bugs  |11/10/2026  |  |  ||
| 4 |Test  |18/10/2026  |  |  ||
| 5 |Wrap up and Report  | 25/10/2026 |  |  ||

| Bug | Explain | In charge | Frontend / Backend |
|---|---|---|---|
| **Yan: Failed submission → change status? Re-apply?** | Frontend needs to display the status and re-apply option; backend needs to store/update application status and handle re-application logic. | Yan | Full stack |
| **Yan 2: Failed 2nd account registration** | Could involve the registration form (frontend) or authentication/database logic (backend). Need the actual error to determine the root cause. | Yan | Full stack |
| **2 hidden — employer portal required** | Backend needs to identify jobs that cannot be automatically applied to; frontend needs to display the appropriate status/message. | Thao | Full stack |
| **Link to the job posts** | Backend needs to provide the job URL; frontend needs to display it as a clickable link. | Thao | Full stack |
| **Keep only 1 CV — remove the modern CV** | Mainly a UI/CV selection issue. If the unwanted CV is stored in the database, backend cleanup may also be needed. | Mahir | Frontend |
| **Preferred locations / countries: dropdown list, add more**<br>**Bug 7: "Remote" listed as a country option** | Mainly a dropdown/multi-select UI change. Backend is only involved if the options come from an API or need to be persisted.<br><br>**Simple explanation:** The country filter includes `"Remote"` alongside actual sovereign nations.<br><br>**How it was found:** Opened Autopilot settings; the country tags list showed: Bangladesh, Canada, Germany, India, Netherlands, Remote, United Kingdom, United States. | Mahir | Frontend |
| **User has to fill in data instead of uploading CV and extracting data** | Frontend needs a profile form; backend needs to receive, validate, and store the profile information. | Mahir | Full stack |
| **Bug 9: Fallback hardcoded string ("Sincerely, Your Name")**<br>**Bug 12: Missing form input sanitization on Profile Update** | **Bug 9:** Clearing the user's name on the profile causes generated cover letters to be signed with the literal dummy text `"Sincerely, Your Name"`.<br><br>**How it was found:** Left Full Name empty on the Profile page, clicked Review & Apply, and the generated letter draft was signed with `"Sincerely, Your Name"`.<br><br>**Bug 12:** Backend accepts invalid URLs and blank strings for required personal details without returning a validation error. | Mahir | Backend |
| **Bug 11: Cascading redundant API re-fetches** | **Simple explanation:** Every button click or tab navigation triggers 2–3 identical API calls at the exact same moment.<br><br>**How it was found:**<br>- Saving profile triggered 3 duplicate calls to `/profile` and `/completeness`.<br>- Opening the apply modal triggered `/api/cv/preview` 3 times simultaneously.<br>- Switching to Autopilot fired duplicate requests for `/autopilot` and `/logs`. | Mahir | Frontend |
| **Others: Mahir's list** | To be reviewed and classified after the individual bugs are provided. | — | — |
