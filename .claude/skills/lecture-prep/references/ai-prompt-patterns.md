# AI Prompt Patterns & Expected Outputs

Common prompts students give to AI coding assistants and likely security issues in the generated code.

## Pattern 1: Feature addition without security context

**Prompt**: "Add a username field to this bulletin board"

**Likely AI output**:
- Adds `username` column to DB
- Adds input field to form
- Renders username via `innerHTML` (same as existing content) — **XSS persists**
- May not validate input length or characters

**Teaching point**: AI follows existing patterns. If the codebase has vulnerabilities, new code inherits them.

## Pattern 2: Error fixing that degrades security

**Prompt**: "I'm getting an error with the database query, fix it"

**Likely AI output**:
- May replace parameterized query `?` with f-string for "simplicity"
- Introduces SQL injection vulnerability

**Teaching point**: AI optimizes for "making it work," not necessarily for security.

## Pattern 3: Bulk feature requests

**Prompt**: "Add likes, comments, and user profiles"

**Likely AI output**:
- Multiple new endpoints without input validation
- New DB tables without proper constraints
- Increased attack surface

**Teaching point**: More features = more attack surface. Each feature needs security review.

## Pattern 4: Copy-paste from AI without review

**Prompt**: "Generate a complete user authentication system"

**Likely AI output**:
- May store passwords in plaintext
- May not implement rate limiting
- Session management may be insecure

**Teaching point**: Never deploy AI-generated security-critical code without thorough review.

## Pattern 5: "Make it production ready"

**Prompt**: "Make this app production ready"

**Likely AI output**:
- May remove `debug=True` (good)
- May add HTTPS redirect (good)
- May miss XSS, CSRF, and other app-level issues
- May not add security headers

**Teaching point**: "Production ready" means different things to AI vs. a security engineer.
