# Documentation Compliance Checklist

This checklist is derived from the Google Styleguide Best Practices and is intended to help review project documentation for compliance.

## 1. Minimum Viable Documentation
- [ ] Write short and useful documents.
- [ ] Cut out everything unnecessary (e.g., out-of-date, incorrect, or redundant information).
- [ ] Continually massage and improve every document to suit changing needs.
- [ ] Keep docs alive but frequently trimmed (like a bonsai tree).

## 2. Update Docs with Code
- [ ] Change documentation in the same CL (Change List/Commit) as the corresponding code change.
- [ ] Ensure docstrings, header files, README.md files, and any other relevant docs are updated alongside the code change (important for reviewers).

## 3. Delete Dead Documentation
- [ ] Actively delete dead (outdated, incorrect) documentation.
- [ ] If documentation is in bad shape, approach cleaning gradually.
- [ ] Prioritize deleting information that is certainly wrong; ignore unclear parts initially.
- [ ] Involve the whole team in reviewing and deciding on documentation (Keep or delete?).
- [ ] Devote specific time for the team to scan and decide on each document.
- [ ] Default to deleting or leaving behind documentation if migrating systems; stragglers can be recovered if necessary.
- [ ] Iterate on the process of cleaning and deleting dead documentation.

## 4. Prefer the Good Over the Perfect
- [ ] Strive for good, useful documentation rather than aiming for an unattainable "perfect" document.

## 5. Documentation is the Story of Your Code
- [ ] Write documentation for humans first, computers second.

### 5.1. Meaningful Names
- [ ] Use good, descriptive naming for all code entities (variables, classes, functions, files, directories) to convey information effectively.

### 5.2. Inline Comments
- [ ] Use inline comments primarily to provide information that the code itself cannot convey (e.g., the rationale or "why" behind the code).

### 5.3. Method and Class Comments
#### Method API Documentation (e.g., header comments, Javadoc, docstrings)
- [ ] Clearly document what methods do and how to use them (this forms the contract of the code's behavior).
- [ ] Ensure that any behavior documented in method comments has a corresponding test verifying it.
- [ ] Detail method arguments, what the method returns, any "gotchas" or restrictions, and what exceptions it can throw or errors it can return.
- [ ] Avoid explaining *why* code behaves a particular way in API documentation; reserve "why" explanations for inline comments.

#### Class / Module API Documentation (e.g., header comments, Javadoc, docstrings)
- [ ] Provide a brief overview of what the class or file does.
- [ ] Include short examples of how the class or file might be used.
- [ ] If there are several distinct ways to use the class (e.g., simple and advanced), always list the simplest use case first in examples.

### 5.4. README.md
- [ ] Ensure the `README.md` orients new users to the directory.
- [ ] Ensure the `README.md` points to more detailed explanations and user guides.
- [ ] Clearly state in the `README.md` what the directory is intended to hold.
- [ ] Indicate in the `README.md` which files a developer should look at first, and specify if some files constitute an API.
- [ ] State in the `README.md` who maintains the directory and where users can find more information or help.
- [ ] Adhere to any project-specific or general `README.md` guidelines (e.g., [Google's README guidelines](https://google.github.io/styleguide/docguide/READMEs.html)).

### 5.5. `docs/` Directory
- [ ] Ensure the `docs/` directory explains how to get started using the relevant API, library, or tool.
- [ ] Ensure the `docs/` directory explains how to run the project's tests.
- [ ] Ensure the `docs/` directory explains how to debug the project's output.
- [ ] Ensure the `docs/` directory explains how to release the binary/software.

### 5.6. Design Docs, PRDs (Product Requirements Documents)
- [ ] After code implementation, ensure design documents and PRDs serve as archives of design decisions, not as partially correct or outdated documentation.

### 5.7. Other External Docs
- [ ] If documentation is maintained in external locations (e.g., Google Sites, Drive, wikis), ensure there are clear pointers to these locations from the project directory (e.g., an obvious link in the project's `README.md`).

## 6. Duplication is Evil
- [ ] Avoid writing custom guides for common technologies or processes if an official or existing guide is available; link to it instead.
- [ ] If an existing guide is missing, incorrect, or badly out of date, submit updates to the appropriate owner/directory or create a package-level `README.md` with the information.
- [ ] Take ownership and contribute to existing documentation rather than duplicating efforts.