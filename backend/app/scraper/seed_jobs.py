"""
Built-in sample job feed so the whole pipeline runs offline and is testable.

Each job carries:
  * source      -> where it was fetched from (LinkedIn, Indeed, company site, ...)
  * country     -> used by the country filter and country-scoped autopilot
  * apply_type  -> "form"     : direct form submission — JobQuest CAN auto-apply
                   "external" : requires logging into an employer portal —
                                JobQuest will NOT apply and hides these from the
                                job list (see jobs router).
"""

SEED_JOBS = [
    # ---------------- LinkedIn (Easy Apply = form submission) ----------------
    {
        "external_id": "li-001", "title": "Frontend Developer Intern",
        "company": "Pixelhive", "location": "Remote", "country": "Remote", "remote": True,
        "url": "https://www.linkedin.com/jobs/view/li-001",
        "source": "LinkedIn", "apply_type": "form",
        "skills": ["JavaScript", "React", "HTML", "CSS", "Git"],
        "requires_cover_letter": False,
        "description": ("Join our product team to build delightful UIs. You'll work "
                        "with React, JavaScript, HTML and CSS, ship features weekly and "
                        "learn from senior engineers. Great for students who love the web."),
    },
    {
        "external_id": "li-002", "title": "Data Analyst Intern",
        "company": "Quantly", "location": "Berlin, Germany", "country": "Germany", "remote": False,
        "url": "https://www.linkedin.com/jobs/view/li-002",
        "source": "LinkedIn", "apply_type": "form",
        "skills": ["Python", "SQL", "Pandas", "Excel", "Statistics"],
        "requires_cover_letter": True,
        "description": ("Analyse product data, build dashboards and communicate insights. "
                        "Comfortable with Python, SQL and Pandas. We value curiosity."),
    },
    {
        "external_id": "li-003", "title": "Machine Learning Intern",
        "company": "Neurabit", "location": "Remote", "country": "Remote", "remote": True,
        "url": "https://www.linkedin.com/jobs/view/li-003",
        "source": "LinkedIn", "apply_type": "form",
        "skills": ["Python", "PyTorch", "Machine Learning", "NumPy", "Git"],
        "requires_cover_letter": True,
        "description": ("Work on real ML models with our research team. Experience with "
                        "Python and PyTorch is a plus. Prototype, evaluate, document."),
    },
    {
        "external_id": "li-004", "title": "Junior Full-Stack Developer",
        "company": "Brightloop", "location": "Toronto, Canada", "country": "Canada", "remote": False,
        "url": "https://www.linkedin.com/jobs/view/li-004",
        "source": "LinkedIn", "apply_type": "form",
        "skills": ["JavaScript", "React", "Node.js", "MongoDB", "Git"],
        "requires_cover_letter": False,
        "description": ("Ship features across the stack with React and Node.js. Good for "
                        "new grads who like variety and fast iteration."),
    },

    # ---------------- Indeed (direct apply form) ----------------
    {
        "external_id": "in-001", "title": "Backend Engineer Intern",
        "company": "Stackforge", "location": "London, UK", "country": "United Kingdom", "remote": False,
        "url": "https://www.indeed.com/viewjob?jk=in-001",
        "source": "Indeed", "apply_type": "form",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker", "REST"],
        "requires_cover_letter": False,
        "description": ("Build and maintain APIs powering our platform. We use Python, "
                        "FastAPI, PostgreSQL and Docker. Own small services end to end."),
    },
    {
        "external_id": "in-002", "title": "QA Automation Intern",
        "company": "Testbed", "location": "Remote", "country": "Remote", "remote": True,
        "url": "https://www.indeed.com/viewjob?jk=in-002",
        "source": "Indeed", "apply_type": "form",
        "skills": ["Playwright", "JavaScript", "Testing", "Git", "Python"],
        "requires_cover_letter": False,
        "description": ("Write automated tests with Playwright and help improve quality. "
                        "Curiosity and attention to detail matter most."),
    },
    {
        "external_id": "in-003", "title": "Marketing Analyst Intern",
        "company": "Groweth", "location": "Remote", "country": "Remote", "remote": True,
        "url": "https://www.indeed.com/viewjob?jk=in-003",
        "source": "Indeed", "apply_type": "form",
        "skills": ["Excel", "SQL", "Analytics", "Communication", "Marketing"],
        "requires_cover_letter": True,
        "description": ("Support growth experiments with data. Comfort with Excel, basic "
                        "SQL and clear writing needed. No prior marketing degree required."),
    },
    {
        "external_id": "in-004", "title": "Software Engineer Intern",
        "company": "Bytenest", "location": "Dhaka, Bangladesh", "country": "Bangladesh", "remote": False,
        "url": "https://www.indeed.com/viewjob?jk=in-004",
        "source": "Indeed", "apply_type": "form",
        "skills": ["Python", "Django", "JavaScript", "SQL", "Git"],
        "requires_cover_letter": False,
        "description": ("Join a fast-growing team building web products. Work with Python, "
                        "Django and JavaScript. Great learning environment for students."),
    },

    # ---------------- Company career pages (direct form) ----------------
    {
        "external_id": "co-001", "title": "UX/UI Design Intern",
        "company": "Formwork", "location": "Remote", "country": "Remote", "remote": True,
        "url": "https://careers.formwork.com/jobs/co-001",
        "source": "Company site", "apply_type": "form",
        "skills": ["Figma", "UI Design", "Prototyping", "User Research"],
        "requires_cover_letter": True,
        "description": ("Design flows and prototypes in Figma, run lightweight user "
                        "research and collaborate with engineers. Portfolio required."),
    },
    {
        "external_id": "co-002", "title": "DevOps Intern",
        "company": "Cloudcrate", "location": "Amsterdam, Netherlands", "country": "Netherlands", "remote": False,
        "url": "https://careers.cloudcrate.io/jobs/co-002",
        "source": "Company site", "apply_type": "form",
        "skills": ["Docker", "Kubernetes", "CI/CD", "Linux", "Python"],
        "requires_cover_letter": False,
        "description": ("Help automate deployments and pipelines. Exposure to Docker, "
                        "Linux and CI/CD tools is helpful. Learn cloud infrastructure."),
    },
    {
        "external_id": "co-003", "title": "Mobile App Developer Intern",
        "company": "Tapstack", "location": "Bangalore, India", "country": "India", "remote": False,
        "url": "https://careers.tapstack.dev/jobs/co-003",
        "source": "Company site", "apply_type": "form",
        "skills": ["Flutter", "Dart", "JavaScript", "Git", "REST"],
        "requires_cover_letter": False,
        "description": ("Build cross-platform apps in Flutter. Any JavaScript or mobile "
                        "experience is welcome. Ship to real users this term."),
    },
    {
        "external_id": "co-004", "title": "Frontend Engineer (New Grad)",
        "company": "Nimbus", "location": "San Francisco, USA", "country": "United States", "remote": False,
        "url": "https://careers.nimbus.com/jobs/co-004",
        "source": "Company site", "apply_type": "form",
        "skills": ["JavaScript", "React", "TypeScript", "CSS", "Git"],
        "requires_cover_letter": True,
        "description": ("Build our customer dashboard in React and TypeScript. New grads "
                        "welcome. Strong fundamentals in JavaScript and CSS expected."),
    },

    # ---------------- External / login-required (EXCLUDED from applying) ----------------
    {
        "external_id": "ex-001", "title": "Data Science Intern",
        "company": "MegaCorp", "location": "New York, USA", "country": "United States", "remote": False,
        "url": "https://megacorp.wd1.myworkdayjobs.com/ex-001",
        "source": "LinkedIn", "apply_type": "external",
        "skills": ["Python", "SQL", "Machine Learning", "Statistics"],
        "requires_cover_letter": True,
        "description": ("Apply on our Workday portal (account required). Data science "
                        "internship working with large datasets."),
    },
    {
        "external_id": "ex-002", "title": "Cloud Engineer Intern",
        "company": "Enterprise Ltd", "location": "London, UK", "country": "United Kingdom", "remote": False,
        "url": "https://boards.greenhouse.io/enterprise/jobs/ex-002",
        "source": "Company site", "apply_type": "external",
        "skills": ["AWS", "Docker", "Python", "Linux"],
        "requires_cover_letter": False,
        "description": ("Apply via our applicant portal (login required). Cloud "
                        "engineering internship."),
    },
]

# All non-remote countries present in the feed, for the filter UI.
def countries() -> list[str]:
    seen = []
    for j in SEED_JOBS:
        if j["apply_type"] == "form" and j["country"] not in seen:
            seen.append(j["country"])
    return sorted(seen)
