import yaml
from urllib.parse import urlparse

def convert_to_rendercv(data: dict) -> str:
    """
    Convert AI agent resume JSON into RenderCV YAML format.
    Returns a YAML string.
    """

    # Extract social usernames from URLs
    def extract_username(url: str) -> str:
        try:
            path = urlparse(url).path.strip("/")
            return path.split("/")[-1] if path else url
        except:
            return url

    cv = {
        "cv": {
            "name": data.get("name"),
            "email": data.get("email"),
            "phone": data.get("phone"),
            "website": data.get("website"),
            "social_networks": [],
            "sections": {},
            "theme": "moderncv",
            "page" : {"show_pagenumbering": False, "show_last_updated_date": False},
            "style": {"header_separator": "none"},
        },
        
    }

    # Socials
    if data.get("linkedin"):
        cv["cv"]["social_networks"].append({
            "network": "LinkedIn",
            "username": extract_username(data["linkedin"])
        })
    if data.get("github"):
        cv["cv"]["social_networks"].append({
            "network": "GitHub",
            "username": extract_username(data["github"])
        })

    # Summary
    if data.get("summary"):
        cv["cv"]["sections"]["summary"] = data["summary"]

    # Experience
    if data.get("experience"):
        cv["cv"]["sections"]["experience"] = []
        for exp in data["experience"]:
            cv["cv"]["sections"]["experience"].append({
                "company": exp.get("company"),
                "position": exp.get("position"),
                "location": exp.get("location"),
                "start_date": exp.get("start_date")[:7] if exp.get("start_date") else None,
                "end_date": exp.get("end_date")[:7] if exp.get("end_date") else None,
                "highlights": exp.get("highlights", [])
            })

    # Education
    if data.get("education"):
        cv["cv"]["sections"]["education"] = []
        for edu in data["education"]:
            cv["cv"]["sections"]["education"].append({
                "institution": edu.get("institution"),
                "area": edu.get("area"),
                "degree": edu.get("degree"),
                "location": edu.get("location"),
                "start_date": edu.get("start_date")[:7] if edu.get("start_date") else None,
                "end_date": edu.get("end_date")[:7] if edu.get("end_date") else None,
                "gpa": edu.get("gpa"),
                "highlights": edu.get("highlights", [])
            })

    # Skills
    if data.get("skills"):
        cv["cv"]["sections"]["technologies"] = []
        for category, details in data["skills"].items():
            cv["cv"]["sections"]["technologies"].append({
                "label": category,
                "details": ", ".join(details)
            })

    # Projects
    if data.get("projects"):
        cv["cv"]["sections"]["projects"] = []
        for proj in data["projects"]:
            cv["cv"]["sections"]["projects"].append({
                "name": proj.get("name"),
                "date": str(proj.get("date")),
                "highlights": proj.get("highlights", [])
            })

    # Certifications
    if data.get("certifications"):
        cv["cv"]["sections"]["certificates"] = data["certifications"]

    # Convert dict → YAML
    return yaml.dump(cv, sort_keys=False, allow_unicode=True)
