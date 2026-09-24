# JobQuest — AI Job-Application Agent for Students

## Stage 1 – Problem Proposal

### 1. Team Information

**Team Name:** JobQuest

**Team Members:**

* Thao Nguyen
* Mahir
* Sijun

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



## 3. Project Scope

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
## 4. Project Board
Tool: GitHub Projects

Create and organize project tasks into milestones and issues.

Main work packages:

Project setup and Docker configuration
User authentication and onboarding
User profile management
Job sourcing and filtering
AI-based job matching and scoring
Tailored CV generation
Cover letter generation
Manual application workflow
Auto-apply functionality
Daily autopilot and scheduling
Application tracking
Preference learning
Dashboard and analytics
Testing and documentation
---
## 5. Architecture Draft

                    ┌──────────────────────┐
                    │       User           │
                    │   Web Browser        │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │   Frontend SPA       │
                    │     Vanilla JS       │
                    │  HTML / CSS / JS      │
                    └──────────┬───────────┘
                               │ REST API
                               ▼
              ┌────────────────────────────────┐
              │          FastAPI Backend        │
              │                                │
              │ ┌──────────┐  ┌─────────────┐ │
              │ │   Auth   │  │   Profile   │ │
              │ └──────────┘  └─────────────┘ │
              │                                │
              │ ┌──────────┐  ┌─────────────┐ │
              │ │   Jobs   │  │Applications │ │
              │ └──────────┘  └─────────────┘ │
              └───────────────┬────────────────┘
                              │
              ┌───────────────┼────────────────┐
              │               │                │
              ▼               ▼                ▼
       ┌────────────┐  ┌─────────────┐  ┌─────────────┐
       │ AI Agents  │  │ Job Scraper  │  │ APScheduler │
       │ Google ADK │  │  Playwright  │  │  Autopilot  │
       └─────┬──────┘  └──────┬──────┘  └─────────────┘
             │                │
             ▼                ▼
       ┌────────────┐   ┌─────────────┐
       │ Job Scorer │   │ Job Sources  │
       │ CV Gen.    │   │ LinkedIn /   │
       │ Cover Ltr. │   │ Indeed / etc.│
       │ Learner    │   └─────────────┘
       └─────┬──────┘
             │
             ▼
       ┌──────────────┐
       │   Database   │
       │    SQLite    │
       │ Users        │
       │ Profiles     │
       │ Jobs         │
       │ Applications │
       │ Preferences  │
       └──────────────┘
