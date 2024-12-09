# Ansible Wrangler


## Table of Contents
- [Members](#members)
- [Progress](#progress)
- [Setup](#setup)
- [Project Overview](#project-overview)
- [How this Solution fits into the RedHat Ecosystem](#how-this-solution-fits-into-the-redhat-ecosystem)
- [Project Visions and Overall Goals](#project-visions-and-overall-goals)
- [Users and Personas of the Project](#users-and-personas)
- [Scope and Features](#scope-and-features)
- [Solution Concept and General Architecture](#solution-concept-and-general-architecture)
- [Design Implications and Discussion](#design-implications-and-discussion)
- [Acceptance Criteria](#acceptance-criteria)
- [Release Planning](#release-planning)
- [General Comments](#general-comments)
- [Resources](#resources)

## Members
| Name | Role | Contact Information |
| :---: | :---: | :---: |
| Ryan Cook | Mentor  | rcook@redhat.com |
| Albert Zhao | Contributor | albertz@bu.edu |
| Reza Sajjadi | Contributor | sajjadi@bu.edu |
| Jack Edelist | Contributor | edelist@bu.edu |
| Arthur Hua | Contributor | ahua102@bu.edu |
| Michael Barany | Contributor | mbarany@bu.edu |
| Alireza Roshandel | Contributor | alirezad@bu.edu |

## Progress
[Sprint 1 Demo](https://drive.google.com/drive/folders/19N2t67B59QdDt1MnHAf7CkfM7lJ14rJK?usp=sharing)

[Sprint 2 Demo](https://drive.google.com/drive/folders/1Zj_zdQ7Hdqzi7-cDt-tku3rnGXbvKtWH?usp=sharing)

[Sprint 3 Demo](https://drive.google.com/drive/folders/1ChZvkJFYUFSo1Nl7DjrvoWRS28i35qFZ?usp=sharing)

[Sprint 4 Demo](https://drive.google.com/drive/folders/1vaU_AqYLK72W9cyWqbyPGBEtvsVrENK1?usp=sharing)

[Sprint 5 Demo](https://drive.google.com/drive/folders/1G4xL2IC2cTTBUZB7TVk2pJHk90gwYuo-?usp=drive_link)

[Final Presentation](https://drive.google.com/drive/folders/1QGru0FKWatIEC660eFXXverskRubWrIA?usp=sharing)

## Setup
1. Clone the main branch of the repository to your machine (where you intend the cloud service to be hosted).
2. Ensure you have the following prerequisites:
   - A **ServiceNow Developer Instance**.
   - An **AWX Administrator Instance**.
3. Embed the following credentials into a configuration (.env) file in the global directory of this repo as specified:
   - AWX_URL (AWX instance)
   - AWX_TOKEN (API key)
   - PROJECT_ID (AWX)
   - INVENTORY_ID (AWX)
   - INSTANCE (ServiceNow dev instance)
   - USERNAME (ServiceNow dev instance)
   - PASSWORD (ServiceNow dev instance)
   - GITHUB_URL (your cloned repo)
   - BRANCH=main
   - EXISTING_DIRECTORY=existing_playbooks
   - OUT_DIRECTORY=wrangler_out
   - CREDENTIAL_ID (AWX)
   - SERVER_LIMIT (AWX)
4. Run `bash start_wrangler.sh` with root privileges.
5. **Note**: If Conda is not installed on your machine, you may need to run the start script **twice** for proper setup.

## Project Overview
The Ansible Wrangler Automation project is an end-to-end solution that integrates ServiceNow incident management with Ansible playbook generation and AWX management and deployment. The goal is to minimize the effort and expertise required to create and deploy Ansible Playbooks in response to incoming incidents. 

This system employs Retrieval Augmented Generation (RAG) to identify relevant existing playbooks and an advanced LLM (qwen2.5-coder:32b) to generate targeted playbooks, ensuring rapid, accurate responses to newly reported incidents. AWX (the open-source upstream project for Red Hat Ansible Platform’s UI) is used to further validate playbooks and manage deployment, allowing for instant corrective action and execution with minimal human intervention.

## How this Solution fits into the RedHat Ecosystem

Some of the Core Components of RedHat’s offerings include the following:
1.	`Ansible Automation Platform` is an open-source automation tool for IT tasks, management, application deployment, provisioning, and orchestration. It allows IT administrators to automate tasks and manage systems more efficiently by writing simple YAML-based playbooks. The YAML playbooks are a set of instructions executed sequentially to automate IT tasks and ensure systems achieve the desired state.
2.	`Ansible Galaxy` is a community hub where users can share and download Ansible roles and collections to build playbooks, but users still need to customize these components manually.
3.	`Ansible Content Collections` are pre-packaged modules, plugins, roles, and playbooks that help automate specific tasks.
4.	`AWX` offers a web-based user interface for managing and orchestrating Ansible playbooks, inventories, and schedules.

As seen above, methods exist to deploy playbooks and find components to build playbooks, but there is no method of automatically generating these playbooks. Creating these playbooks remains a manual task that typically requires expertise in Ansible. The `Ansible Wrangler Automation Project` fills the gap by automating the generation of playbooks in response to reported incidents (done through service now in this implementation)

## Project Visions and Overall Goals
Our vision is to reduce manual efforts involved in incident management and solution playbook creation by streamlining the process of generating, managing, and deploying playbooks in Ansible in response to incidents reported by ServiceNow users. 

This system:
- Automates the process of creating appropriate Ansible playbooks via the Ollama AI model based on the user's reported incident.
- It also checks for pre-existing playbooks in the GitHub repository using RAG. It will then determine if a suitable playbook exists and return it to the user. 
- If no suitable playbook exists, the system will dynamically generate one based on its understanding of the error, the provided description, and historical data similar to this issue using Ollama.
- The ideal playbook will then automatically be fed into Redhat's Ansible to be verified, run, and deployed. And the ideal playbook will be stored into a git repo for future use. 

Overall, this project should reduce the time between reporting an error and getting feedback from another software developer/or IT personal by having a solution be generated immediately. This should allow more people to be able to use Ansible and fix any issues without having in-depth knowledge about how to fine-tune their system and help teams efficiently address issues.

## Users and Personas
**Site Reliability Engineer (SRE)**  

**Key Characteristics:** Site Reliability Engineers are responsible for ensuring the high availability, performance, and security of infrastructure. They frequently respond to incidents and investigate operational issues, often utilizing tools like Ansible along with monitoring platforms such as Prometheus and Grafana. SREs need rapid and reliable solutions for infrastructure problems and are comfortable working with playbooks and scripts.  

**Primary Actions:** In this project, SREs receive alerts about system issues, review and approve Ansible playbooks generated by Ansible Wrangler, and initiate their execution to resolve detected issues. They also provide valuable feedback on playbook performance to improve future remediations.
  
**System Administrator (SysAdmin)**  

**Key Characteristics:** System Administrators manage and maintain the core Linux and Kubernetes infrastructure and are often the first point of contact for infrastructure-related issues. They oversee repositories of standard playbooks, updating them as system changes occur, and seek opportunities to streamline repetitive tasks through automation. 

**Primary Actions:** For this project, SysAdmins review and refine playbooks generated by Ansible Wrangler before merging them into production. They suggest improvements to existing playbooks for more efficient operation and ensure that system updates or configurations are effectively integrated into playbooks.


## Scope and Features
**ServiceNow Integration**
- Automatically connects to ServiceNow to fetch unresolved incidents using specified user credentials.
- Updates the state of incidents in ServiceNow after processing, including adding comments, tracking incident states, and marking them as resolved when successfully addressed.
- ServiceNow Interface (SNOW): Users will be able to submit incidents and see solution/playbook in the incident activity section.
  
**AI-Generated Playbooks**
- Generates Ansible playbooks using the LLaMA language model when no suitable playbook is found in the repository.
- Provides users with the option to either retrieve a relevant existing playbook or request the generation of a new one.
  
**Existing Playbook Retrieval**
- Implements a FAISS-based retrieval system to search a repository of indexed Ansible playbooks.
- Ranks and retrieves the top-k most relevant playbooks based on the incident description to minimize redundant generation.
  
**GitHub Integration**
- Automatically saves generated or selected playbooks to a designated GitHub repository.
- Commits changes, pushes them to the specified branch, and synchronizes with AWX for deployment.
  
**AWX Automation**
We integrated our system with AWX to:
  - Trigger project updates.
  - Create job templates for new playbooks.
  - Launch and track jobs for Ansible playbook execution.
  - Ensure seamless deployment of playbooks to manage servers and resolve incidents on the cloud.
  
**Interactive Incident Handling**
- We can retrieve the most recent comment from the activity section in an incident report on ServiceNow
- Monitors comments on ServiceNow incidents to allow users to:
  - Search for existing playbooks.
  - Generate new playbooks dynamically using AI.
  - Select and deploy a playbook by responding to the system’s prompts.
    
**End-to-end Pipeline**
- A fully automated pipeline that spans incident detection, playbook retrieval/generation, deployment, and resolution tracking that supports multiple instances as a persistent cloud service.

## Additional Features to be Considered
These are some of the features that we could implement after the completion of our main objectives. 
- Incident Feedback Loop: 
  - implement feedback mechanism for SREs to rate effectiveness of generated playbooks
- Incident categorization: 
  - use generative AI to categorize incidents into different severity levels and assign relevant actions or workflows automatically
- ChatOps Integration: 
  - integrate with Slack, Microsoft Teams or other chat platforms to allow playbook generation within team chats, or direct access through 1-on-1 chat with an Ansible Wranger “bot”
- Further Cloud and Queue Integration:
  - Using different queue structures to prioritize different tasks and requests when handling a large load of incident requests. 

## Solution Concept and General Architecture
This project follows a modular architecture that integrates several components to automate incident handling and playbook generation. Below is a general architectural overview and workflow of the project: 
Architectural components:
1. ServiceNow: This is the starting point of the workflow, where incidents are generated and managed. We will utilize ServiceNow API and SNOW interface to fetch incidents.
2. Automation: The core of this automation engine that:
   - Incident Retrieval: get incidents created by users from ServiceNow.
   - Playbook Search Module: searches for existing playbooks in a GitHub repo to check for a match with the incident description
   - Llama Interaction: if no match is found, this module generates a new Ansible playbook using the Llama model based on the description of the incident.
   - GitHub API Integration: Automatically submits a pull request to a specific GitHub repo for the newly generated playbook. This stores all the existing playbooks.
   - AWX: validation and deployment of the selected playbook.
   - Incident State Updater: Updates the state of the incident in ServiceNow to notify the user about the action taken (through ServiceNow activity/comments).
3. GitHub Repository: A version control system where the existing playbooks are stored, and new playbooks are committed. We will be using the GitHub API to manage the repository, branches, commits, and pull requests. 
4. Llama: The natural language processing model (GPT) that interprets incident descriptions and generates Ansible playbooks.

Our module communication chart:

<img width="963" alt="image" src="https://github.com/user-attachments/assets/11055652-c54b-43c9-b44f-d41039fee3bb">

Detailed Process chart:

<img width="757" alt="image" src="https://github.com/EC528-Fall-2024/ansible-wrangler/blob/main/workflow1.png">


## Design Implications and Discussion
1. **API-Driven Architecture**: The decision to use an API-driven architecture ensures flexibility and scalability. By integrating with ServiceNow, Gen AI API, and GitHub APIs, the system is modular and can easily be expanded to include other services in the future.
2. **AI-Driven Playbook Generation**: allows the system to automatically create customized and relevant Ansible playbooks based on incident descriptions. This reduces manual intervention and accelerates incident resolution. Using a pre-trained model also enhances efficiency while ensuring that the system can adapt to various types of incidents with minimal human input.
3. **Automation-First Approach**: The whole point of this project is to use automation to speed up incident reports. By eliminating manual steps, the system can quickly respond to incidents, reducing resolution times and ensuring a consistent, repeatable workflow.

## Acceptance Criteria
We want to make sure that the core functionality of the Ansible Wrangler Automation project is met. To ensure this, essential features and capabilities must be implemented and verified for this project to be complete. Essential features include:
- ServiceNow (SNOW interface) incident retrieval
- Existing playbook search algorithm
- LLM playbook generation
- Git version control integration
- AWX deployment
- ServiceNow incident update
- SNOW feedback loop & persistent cloud service

## Release Planning
This project will be delivered in a series of iterative releases, each introducing new features and functionality incrementally. 

### Release overview
Each release will focus on a specific set of features, starting with the core functionality of the system and expanding to include advanced capabilities such as playbook validation, error handling, and enhanced integration. 

#### First Sprint Study, Research and Core Infrastructure Setup

In the first sprint, we focused on researching all the necessary frameworks, structures, and APIs for this project. We researched multiple LLMS (OpenAI and Llama) to see which model is faster and more efficient for Ansible playbook generation. We also researched Rest API to see how data can be transferred between different modules within our project. We also investigated different cloud services and structures to apply the best cloud application. 

#### Second Sprint: Core Functionality

The goal of the second sprint is to establish the core structure of the Ansible Wrangler Automation system and implement basic functionalities that enable the system to handle incidents efficiently. 
- Develop a simple and intuitive front-end interface where users can submit incident requests. This interface will collect relevant information such as the error description, code snippets (if applicable), urgency, state of the issue, and any additional context needed to resolve the issue.
  - This interface could be integrated into existing chat platforms like Slack, or it could be a standalone web form that communicates with the backend system via REST API calls.
- Implement a search algorithm to scan the existing repository of playbooks for a match.
- Integrate a LLaMA Language Model dynamically generate new Ansible playbooks when no suitable existing playbook is found.
- The system will analyze the incident description and any provided code to create a customized playbook. This playbook will be in YAML format and structured to resolve the issue step-by-step.
  

#### Third Sprint: GitHub Integration and Pull Requests 

#### Fourth Sprint: Advanced Features and Stretch Goals

Key Deliverables Per Release
- Release 1: Core system infrastructure, logging, and initial API connections.
- Release 2: Full playbook generation pipeline, including incident retrieval, GPT-based generation, and playbook commits.
- Release 3: GitHub integration with pull request creation, validation, and error handling.
- Release 4: Advanced features, scalability improvements, and user notifications.

Each sprint will conclude with a sprint review, where feedback will be collected to guide the next sprint. The first release is expected to provide the foundational elements of the system, with each subsequent release building upon it and adding more advanced features.


## General Comments
We plan to scale this project based on the available timeline, with the potential to expand its functionality and incorporate additional features. As the project progresses, we will evaluate opportunities for enhanced automation, improved playbook matching algorithms, and integration with other platforms to make sure the system remains flexible and adaptable to future needs/progress. 

## Resources
https://github.com/cooktheryan/wrangler

https://docs.ansible.com/
