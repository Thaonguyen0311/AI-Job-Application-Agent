# JobQuest — AI Job-Application Agent for Students

## Stage 1 – Problem Proposal

### 1. Team Information

**Team Name:** JobQuest

**Team Members:**

* Thao Nguyen
* Mahir
* Sijun

**Team Leader:** Thao Nguyen

**Initial Project Area:**
AI-powered job application automation and career assistance

---

## 2. Problem Statement

Finding and applying for internships, student jobs, and graduate positions is a repetitive and time-consuming process, especially for students applying to many positions.

Students typically need to search across multiple job platforms, determine whether a position matches their skills and preferences, adapt their CV for different job descriptions, write cover letters, and keep track of submitted applications. When applying to many positions, this process becomes difficult to manage consistently.

Another challenge is that students often use the same CV for different positions even though different jobs emphasize different skills and requirements. This can reduce the relevance of their applications.

The problem occurs during the job-search and application process. The main users are students and recent graduates who need to apply for multiple positions while managing their studies or other responsibilities.

JobQuest addresses this problem by providing an AI-assisted workflow that combines job discovery, job matching, CV tailoring, cover-letter generation, application management, and optional automated application.

---

## 3. Users / Stakeholders

### Primary Users

**Students and recent graduates**

They benefit from:

* Finding relevant job opportunities
* Quickly understanding how well a job matches their profile
* Creating a tailored CV for each position
* Preparing cover letters
* Reviewing applications before submission
* Tracking application progress
* Reducing repetitive application work

### Secondary Stakeholders

**Recruiters / employers**

They may benefit indirectly because applications can be more relevant to the advertised position and better structured.

**Universities and career services**

The system could potentially support students with a more organized and efficient job-search process.

---

## 4. Current Situation

Currently, students often manage the job application process manually.

A typical workflow is:

1. Search for jobs on several websites.
2. Open individual job advertisements.
3. Read the job description.
4. Compare the requirements with personal skills and experience.
5. Modify the CV manually.
6. Write or modify a cover letter.
7. Submit the application.
8. Record the application somewhere manually.
9. Check the application status later.

This process has several limitations:

* It takes considerable time.
* The same information must be entered repeatedly.
* Students may apply to jobs that are not a good match.
* CV tailoring is often inconsistent.
* Applications can be difficult to track.
* Students may lose useful information about which types of jobs produce better results.

JobQuest combines these steps into one workflow. The current project already supports job filtering by country, source, and match score, as well as per-job CV tailoring and application tracking.

---

## 5. Proposed Improvement

JobQuest is an AI-powered job-application copilot designed specifically for students.

The user creates a profile once with information such as education, skills, languages, preferred roles, preferred countries, and work experience.

JobQuest then helps the user:

* Find relevant jobs.
* Calculate a match score between the user's profile and a job.
* Generate a CV tailored to the specific position.
* Generate an editable cover letter.
* Review the application before submitting.
* Apply manually or automatically where supported.
* Track submitted applications.
* Learn from application outcomes.

The system also allows users to define preferred countries so that automated applications remain within their selected geographic preferences.

The goal is not simply to automate applications, but to reduce repetitive work while giving the student control over the application process.

---

## 6. Expected Value

### Time Savings

Students spend less time repeatedly modifying CVs, writing cover letters, and organizing applications.

### Reduced Manual Work

The system combines job matching, document generation, application submission, and tracking into one workflow.

### Better Application Relevance

CVs are adapted to individual job descriptions, with relevant skills prioritized for the target position.

### Improved Visibility

A dashboard allows users to see application statistics, application statuses, and job-match information.

### Personalized Job Search

The system learns from application outcomes. Positive outcomes increase the importance of related skills, while rejected applications can reduce the weight of associated skills in future matching.

### Better User Experience

Instead of managing many separate tools, students can use one system for a large part of their job-search workflow.

---

## 7. Initial Technical Challenge

The project combines several technical areas:

* Artificial intelligence and LLM-based content generation
* Job matching and similarity scoring
* Automated document generation
* Web application development
* Web automation
* Scheduled background tasks
* Database management
* API development
* Containerized deployment

The existing system uses FastAPI, Google ADK, Playwright, APScheduler, and a browser-based frontend deployed through Docker Compose.

---

## 8. Project Scope

### Minimum Viable Product

The MVP should demonstrate the complete core workflow:

**User profile → Job discovery → Job matching → Tailored CV → Cover letter → Review → Application → Application tracking**

The MVP should include:

1. User registration and login.
2. User profile and preferences.
3. Sample job database.
4. Job filtering.
5. Job matching score.
6. Job-specific CV generation.
7. Cover-letter generation.
8. Review and editing before application.
9. Application submission simulation.
10. Application history and status tracking.
11. Basic dashboard.

Automatic daily application can be treated as an additional feature after the core MVP is working.

The existing project already provides a demo/seed mode that simulates applications without interacting with third-party websites, making it suitable for a controlled course demonstration.
