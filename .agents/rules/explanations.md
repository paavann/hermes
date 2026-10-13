---
trigger: always_on
---

# Project & Code Explanations Standards

When providing explanations regarding the project, codebase, or architecture, strictly adhere to the following guidelines:

- **Deeply Technical Focus ("The Why")**: Explanations must go deeply technical. Focus heavily on the "why" — detailing architectural decisions, tradeoffs, and underlying mechanisms — rather than just describing the "what" (what the code does).
- **Mandatory Tool & Dependency Audit**: For every explanation that involves specific tools, libraries, or frameworks, you MUST consult the documentation of the latest version of those tools. Ensure the project's current usage aligns with the latest best practices. If the usage is outdated, you must proactively suggest modernizations or discovered changes.
- **Industry Standards Verification**: You MUST actively verify whether the user and the codebase are following clean, conventional, and industry standards across the board. This includes evaluating code quality, proper usage of tools, directory/folder structure, and ensuring configuration files are set up correctly. Proactively call out any deviations from established best practices.
- **Paced Learning for Large Scopes**: When explaining something extensive or large-scale (such as an entire backend, a major feature, or multi-file architecture), you MUST break the explanation down into logical, manageable parts. Do not explain the entire system at once. Instead, present one part, prompt a discussion to ensure the user has clearly understood that specific piece, and wait for their confirmation or questions before moving on to the next part.
- **Inline Format**: Provide these extensive explanations directly in the chat interface using standard markdown. Do not create separate artifact files for explanations unless explicitly asked.
- **Organic but Comprehensive Structure**: While there is no strict template, the structure should evolve organically based on the specific question asked. However, EVERY extensive explanation must satisfy the following core requirements:
  1. **Context & Architecture**: Clearly explain the "what" and the "why".
  2. **Under the Hood**: Deep dive into mechanisms, performance implications, and tradeoffs.
  3. **Tool & Dependency Audit**: Explicitly mention the latest documentation check for relevant tools.
  4. **Modernization Suggestions**: Propose actionable updates if current usage is deprecated or suboptimal.
- **Tone & Assumptions**: Maintain an authoritative but consultative tone. Confidently explain the architecture and provide direct URLs/links to the latest tool documentation. If any context is missing, explicitly state the assumptions you are making before proceeding.
