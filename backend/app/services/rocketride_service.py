import asyncio
import json
import logging
from typing import Any, Dict, List, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

ANALYZE_SYSTEM_PROMPT = """You are an expert code reviewer evaluating Pull Requests for a complex open-source software project.

You have access to all previously analyzed PRs in the vector database. Use that context to identify duplicates.

Respond ONLY with a valid JSON object — no markdown, no explanation, no code fences.

The JSON must have exactly these fields:
{
  "topics": ["topic1", "topic2"],
  "summary": "Brief 1-2 sentence description of what the PR does",
  "recommendation": "merge|keep|discard|combine",
  "score": 75,
  "reasoning": "Explanation of the score and recommendation",
  "similar_prs": []
}

For similar_prs: include PR numbers (integers) of any PRs already in the database that are very similar or duplicate. Leave empty array if none found.

Topics must be from: vectordb, engine, llms, integrations, ui, bugfix, docs, testing, devops, other

Scoring guide (be strict):
- 85-100: Production-ready, well-tested, solves a real problem clearly
- 65-84: Good work, needs minor improvements or tests
- 40-64: Interesting but incomplete, lacks tests, or has design issues
- 0-39: Low quality, vague, duplicate, or not ready

Recommendations:
- merge: Ready to merge as-is (score >= 85)
- keep: Worth reviewing, needs work (score 40-84)
- discard: Not worth merging — vague, broken, or purely cosmetic (score < 40)
- combine: Overlaps significantly with another PR, should be merged together"""

VIABILITY_PROMPT = """Based on the engineering patterns and coding standards from our senior engineers stored in the vector database, assess this Pull Request.

Compare the PR's code quality, architecture decisions, testing approach, and coding patterns against the established engineering standards.

Respond ONLY with a valid JSON object (no markdown, no code fences):
{
  "viability_score": 0-100,
  "strengths": ["specific strength 1", "specific strength 2"],
  "weaknesses": ["specific weakness 1", "specific weakness 2"],
  "recommendations": ["actionable recommendation 1", "actionable recommendation 2"],
  "overall_assessment": "1-2 sentence summary of viability"
}"""

COMMENT_ANALYSIS_PROMPT = """Analyze whether the following review comments have been addressed in the current code diff.

For each comment, determine if the feedback was:
- "applied": The code clearly implements the suggested change
- "partial": Some aspects were addressed but not fully
- "not_applied": The comment was not addressed in the current code

Respond ONLY with a valid JSON array (no markdown, no code fences):
[
  {
    "author": "commenter name",
    "body": "original comment (truncated)",
    "status": "applied|partial|not_applied",
    "explanation": "Brief explanation of why this status"
  }
]"""

TICKET_EVALUATION_PROMPT = """You are a senior technical lead evaluating whether a GitHub issue/ticket makes sense for the project.

Analyze the ticket and the associated PR implementation. Assess:
1. Does the ticket describe a real need, or is it redundant with existing functionality?
2. Could this change be counterproductive or introduce regressions?
3. Does the PR implementation actually match what the ticket asks for?
4. Is there anything in the ticket or implementation that is unclear or risky?

Respond ONLY with a valid JSON object (no markdown, no code fences):
{
  "ticket_makes_sense": true/false,
  "implementation_matches_ticket": true/false,
  "is_redundant": true/false,
  "is_counterproductive": false,
  "risk_level": "low|medium|high|critical",
  "risk_reasons": ["reason 1 if any"],
  "ticket_assessment": "1-2 sentence opinion about the ticket's value",
  "implementation_assessment": "1-2 sentence opinion about whether the code does what the ticket says",
  "needs_human_review": false,
  "human_review_reason": "Explain why a human should look at this (empty string if not needed)"
}

Set needs_human_review=true when:
- The ticket's purpose is ambiguous or could be interpreted multiple ways
- The change could break existing behavior but you're not sure
- The implementation diverges significantly from the ticket
- risk_level is "high" or "critical"
- The ticket seems to duplicate or conflict with another existing feature"""

REVIEW_GENERATION_PROMPT = """You are a friendly and supportive senior engineer reviewing a teammate's Pull Request. Write as a real person who genuinely wants to help — warm, encouraging, and constructive. Never sound robotic, cold, or like a template.

Tone guidelines:
- Start by thanking the author or acknowledging the effort behind the PR.
- Lead with what's good before mentioning what could improve — people respond better to praise first.
- When suggesting changes, frame them as collaborative ("What do you think about…", "One thing we could consider…", "Small suggestion:") rather than commands.
- Use a natural, conversational voice — like a colleague you'd enjoy working with.
- Be specific: reference files, functions, or decisions so the author knows exactly what you mean.
- End on a positive or encouraging note, even when requesting changes.

Your review must cover:
1. Genuine appreciation for what the PR does well
2. Whether previous review comments were addressed (be specific, not vague)
3. Whether the linked ticket/issue makes sense (if provided)
4. Constructive feedback on any concerns, framed helpfully
5. A clear, friendly verdict

Respond ONLY with a valid JSON object (no markdown, no code fences):
{
  "body": "Your review in markdown. Warm and human — like a supportive tech lead who cares about the team. Reference specific files, patterns, or decisions.",
  "event": "APPROVE|REQUEST_CHANGES|COMMENT",
  "risk_level": "low|medium|high|critical",
  "needs_human_review": false,
  "human_review_reason": ""
}

Rules:
- APPROVE only if everything looks solid: viability >= 85, comments addressed, ticket makes sense
- REQUEST_CHANGES if there are real issues — but always pair the request with encouragement and clear guidance on what to fix
- COMMENT if you have thoughts but nothing blocking
- Set needs_human_review=true if risk_level is "high"/"critical" or if you're uncertain about impact
- When needs_human_review is true, explain in human_review_reason what the human should look at"""


# ---------------------------------------------------------------------------
# Singleton rocketride client
# ---------------------------------------------------------------------------

class RocketrideClient:
    """
    Singleton wrapper around the rocketride Python SDK.
    Keeps a persistent WebSocket connection and a single pipeline token
    alive for the lifetime of the application.
    """

    def __init__(self):
        self._client = None
        self._token_webhook: Optional[str] = None
        self._token_criteria: Optional[str] = None
        self._lock = asyncio.Lock()
        self._ready = False
        self._criteria_ready = False

    async def startup(self):
        """Connect to rocketride and start both pipeline sources."""
        try:
            from rocketride import RocketRideClient as _SDK
            # Map project .env vars to the ROCKETRIDE_* names the pipeline expects (${ROCKETRIDE_*} substitution)
            anthropic_key = (
                (settings.rocketride_anthropic_apikey or settings.anthropic_api_key or "").strip()
            )
            if settings.debug:
                key_src = (
                    "ROCKETRIDE_ANTHROPIC_APIKEY"
                    if (settings.rocketride_anthropic_apikey or "").strip()
                    else "ANTHROPIC_API_KEY"
                    if (settings.anthropic_api_key or "").strip()
                    else "(ninguna — clave vacía)"
                )
                logger.info(
                    "[rocketride] Clave Anthropic para el pipeline: origen=%s, longitud=%s",
                    key_src,
                    len(anthropic_key),
                )
            pipeline_env = {
                "ROCKETRIDE_ANTHROPIC_APIKEY": anthropic_key,
                "ROCKETRIDE_OPENAI_KEY": (settings.openai_api_key or "").strip(),
                "ROCKETRIDE_QDRANT_HOST": settings.qdrant_url,
                "ROCKETRIDE_QDRANT_APIKEY": settings.qdrant_api_key or "",
            }
            self._client = _SDK(
                uri=settings.rocketride_url,
                auth=settings.rocketride_api_key or "",
                persist=True,
                max_retry_time=60_000,
                env=pipeline_env,
            )
            # Patch missing method in SDK v1.0.4
            if not hasattr(self._client, '_debug_message'):
                self._client._debug_message = lambda msg: logger.debug(f"[rocketride] {msg}")
            await self._client.connect()
            # Wait for WebSocket handshake to complete
            for attempt in range(10):
                if getattr(self._client, '_connected', False) or getattr(self._client, 'is_connected', lambda: False)():
                    break
                logger.info(f"Waiting for rocketride connection... ({attempt + 1}/10)")
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(2)
            pipe = f"pipeline/{settings.rocketride_pipeline}.pipe"
            r1 = await self._client.use(filepath=pipe, source="webhook_1")
            self._token_webhook = r1["token"]
            self._ready = True
            logger.info(f"Rocketride ready. webhook={self._token_webhook}")

            # Start criteria pipeline
            try:
                pipe_criteria = f"pipeline/{settings.rocketride_criteria_pipeline}.pipe"
                r2 = await self._client.use(filepath=pipe_criteria, source="webhook_1")
                self._token_criteria = r2["token"]
                self._criteria_ready = True
                logger.info(f"Rocketride criteria ready. token={self._token_criteria}")
            except Exception as e:
                logger.warning(f"Criteria pipeline startup failed (non-blocking): {e}")
                self._criteria_ready = False
        except ImportError:
            raise RuntimeError("rocketride SDK not installed. Run: pip install rocketride")
        except Exception as e:
            raise RuntimeError(f"Rocketride startup failed: {e}")

    async def shutdown(self):
        """Terminate pipeline tokens and disconnect."""
        for token in (self._token_webhook, self._token_criteria):
            if self._client and token:
                try:
                    await self._client.terminate(token)
                except Exception:
                    pass
        if self._client:
            try:
                await self._client.disconnect()
            except Exception:
                pass
        self._ready = False
        self._criteria_ready = False

    async def _ensure_tokens(self):
        """Re-acquire the webhook token if missing."""
        async with self._lock:
            if self._token_webhook:
                self._ready = True
                return
            if not self._client:
                return
            pipe = f"pipeline/{settings.rocketride_pipeline}.pipe"
            try:
                r1 = await self._client.use(filepath=pipe, source="webhook_1")
                self._token_webhook = r1["token"]
                self._ready = True
                logger.info(f"[rocketride] webhook token re-acquired: {self._token_webhook}")
            except Exception as e:
                logger.warning(f"Rocketride webhook token refresh failed: {e}")

    # ------------------------------------------------------------------
    # PR ingestion via webhook path (send)
    # ------------------------------------------------------------------

    async def send_pr(self, pr_text: str, pr_number: int) -> bool:
        """Send PR content via webhook source for embedding + storage in Qdrant."""
        if not self._ready:
            return False
        await self._ensure_tokens()
        try:
            await self._client.send(
                self._token_webhook,
                pr_text,
                objinfo={"name": f"pr_{pr_number}.txt"},
                mimetype="text/plain",
            )
            return True
        except Exception as e:
            logger.warning(f"Rocketride send_pr failed for PR #{pr_number}: {e}")
            return False

    # ------------------------------------------------------------------
    # Chat via chat source path
    # ------------------------------------------------------------------

    async def chat(self, message: str, history: List[Dict[str, str]] = None) -> Optional[str]:
        """Send a question via the webhook using application/rocketride-question MIME."""
        if not self._ready:
            logger.warning("[rocketride] chat called but client is not ready — attempting token refresh")
            await self._ensure_tokens()
        if not self._ready:
            logger.error("[rocketride] chat aborted — client still not ready after refresh")
            return None
        history = history or []
        try:
            from rocketride.schema import Question, QuestionHistory
            question = Question()
            for h in history[-10:]:
                question.addHistory(QuestionHistory(role=h["role"], content=h["content"]))
            question.addQuestion(message)
            result = await self._client.send(
                self._token_webhook,
                question.model_dump_json(),
                objinfo={"name": "chat_query"},
                mimetype="application/rocketride-question",
            )
            logger.info(f"[rocketride] chat raw result type={type(result).__name__} value={str(result)[:500]}")
            answer = self._extract_answer(result)
            logger.info(f"[rocketride] chat extracted answer: {str(answer)[:200] if answer else None}")
            return answer
        except Exception as e:
            logger.error(f"[rocketride] chat exception: {type(e).__name__}: {e}", exc_info=True)
            return None

    # ------------------------------------------------------------------
    # Criteria pipeline: commit ingestion + pattern queries
    # ------------------------------------------------------------------

    async def send_commit(self, commit_text: str, commit_sha: str) -> bool:
        """Send commit content to the criteria pipeline for embedding + storage."""
        if not self._criteria_ready:
            return False
        try:
            await self._client.send(
                self._token_criteria,
                commit_text,
                objinfo={"name": f"commit_{commit_sha[:8]}.txt"},
                mimetype="text/plain",
            )
            return True
        except Exception as e:
            logger.warning(f"Rocketride send_commit failed for {commit_sha[:8]}: {e}")
            return False

    async def chat_criteria(self, message: str, history: List[Dict[str, str]] = None) -> Optional[str]:
        """Send a question to the criteria pipeline for engineering pattern analysis."""
        if not self._criteria_ready:
            logger.warning("[rocketride] chat_criteria called but criteria pipeline not ready")
            return None
        history = history or []
        try:
            from rocketride.schema import Question, QuestionHistory
            question = Question()
            for h in history[-10:]:
                question.addHistory(QuestionHistory(role=h["role"], content=h["content"]))
            question.addQuestion(message)
            result = await self._client.send(
                self._token_criteria,
                question.model_dump_json(),
                objinfo={"name": "criteria_query"},
                mimetype="application/rocketride-question",
            )
            return self._extract_answer(result)
        except Exception as e:
            logger.error(f"[rocketride] chat_criteria exception: {e}", exc_info=True)
            return None

    def _extract_answer(self, value: Any) -> Optional[str]:
        """Recursively extract the answer text from any Rocketride response structure."""
        if value is None:
            return None
        if isinstance(value, str):
            return value if value.strip() else None
        if isinstance(value, list):
            if not value:
                return None
            return self._extract_answer(value[0])
        if isinstance(value, dict):
            # Navigate known wrapper keys first
            for key in ("body", "answers", "answer", "content", "text", "message", "response"):
                v = value.get(key)
                if v:
                    extracted = self._extract_answer(v)
                    if extracted:
                        return extracted
            # Last resort: stringify the whole dict
            return json.dumps(value)
        return str(value)


# Module-level singleton
rocketride = RocketrideClient()


# ---------------------------------------------------------------------------
# RocketrideService — high-level interface used by API routes
# ---------------------------------------------------------------------------

class RocketrideService:

    # ------------------------------------------------------------------
    # PR Analysis
    # ------------------------------------------------------------------

    async def analyze_pr(self, pr_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build a plain-text representation of the PR, send it to the
        pipeline (webhook path → embedding → Qdrant), then ask the LLM
        to analyze it (chat path → Qdrant context → LLM).
        """
        title = pr_data.get("title", "")
        description = (pr_data.get("description") or "")[:2000]
        files = pr_data.get("files", [])
        diff = (pr_data.get("diff") or "")[:3000]

        files_str = "\n".join(files[:30]) if files else "No files listed"
        pr_text = (
            f"PR #{pr_data.get('number')} — {title}\n\n"
            f"Description:\n{description}\n\n"
            f"Files changed:\n{files_str}\n\n"
            f"Diff:\n{diff}"
        )

        # 1. Store in Qdrant via webhook path
        ok = await rocketride.send_pr(pr_text, pr_data.get("number", 0))
        if not ok:
            raise RuntimeError("Rocketride send_pr failed — pipeline unavailable")

        # 2. Ask the LLM via chat path
        analyze_prompt = (
            f"{ANALYZE_SYSTEM_PROMPT}\n\n"
            f"Analyze this PR:\n{pr_text[:4000]}"
        )
        answer = await rocketride.chat(analyze_prompt)
        if not answer:
            raise RuntimeError("Rocketride chat returned no answer")

        return self._parse_analysis_json(answer)

    # ------------------------------------------------------------------
    # Chat about PRs
    # ------------------------------------------------------------------

    async def chat_about_pr(
        self,
        message: str,
        history: List[Dict[str, str]] = None,
        pr_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Chat about a PR. Qdrant already holds all PR embeddings so the
        pipeline retrieves relevant context automatically.
        """
        history = history or []

        # Prepend PR context hint if available
        if pr_context:
            ctx = (
                f"[Context: PR #{pr_context.get('number')} — {pr_context.get('title')}. "
                f"Topics: {', '.join(pr_context.get('topics', []))}. "
                f"Score: {pr_context.get('score')}/100.] "
            )
            full_message = ctx + message
        else:
            full_message = message

        answer = await rocketride.chat(full_message, history)
        if not answer:
            raise RuntimeError("Rocketride chat returned no answer")
        return answer

    # ------------------------------------------------------------------
    # Commit criteria ingestion
    # ------------------------------------------------------------------

    async def ingest_commits(self, commits: List[Dict[str, Any]]) -> int:
        """Ingest commit/PR data into the criteria pipeline. Returns success count."""
        success = 0
        for commit in commits:
            files_str = "\n".join(
                f"  {f['filename']} (+{f['additions']}/-{f['deletions']})"
                for f in commit.get("files", [])[:15]
            )
            patches = "\n\n".join(
                f"--- {f['filename']} ---\n{f['patch']}"
                for f in commit.get("files", [])[:10]
                if f.get("patch")
            )
            # Use PR diff if available (richer than individual file patches)
            diff_section = commit.get("diff", "") or patches
            commit_text = (
                f"Engineering contribution by {commit.get('author_name', '')} <{commit.get('author_email', '')}>\n"
                f"Date: {commit.get('date', '')}\n"
                f"Reference: {commit.get('sha', '')}\n\n"
                f"Description:\n{commit.get('message', '')}\n\n"
                f"Files changed:\n{files_str}\n\n"
                f"Code changes:\n{diff_section}"
            )
            ok = await rocketride.send_commit(commit_text, commit.get("sha", "unknown"))
            if ok:
                success += 1
        return success

    # ------------------------------------------------------------------
    # Viability assessment using criteria pipeline
    # ------------------------------------------------------------------

    async def assess_viability(
        self,
        pr_data: Dict[str, Any],
        pr_comments: List[Dict[str, Any]] = None,
        diff: str = "",
    ) -> Dict[str, Any]:
        """Assess PR viability against engineering criteria from stored commits."""
        title = pr_data.get("title", "")
        description = (pr_data.get("description") or "")[:2000]
        files = pr_data.get("filesChanged") or pr_data.get("files_changed") or []
        files_str = "\n".join(files[:30]) if files else "No files listed"

        prompt = (
            f"{VIABILITY_PROMPT}\n\n"
            f"PR #{pr_data.get('number')} — {title}\n"
            f"Description: {description}\n"
            f"Files changed:\n{files_str}\n"
        )
        if diff:
            prompt += f"\nDiff (excerpt):\n{diff[:3000]}\n"

        answer = await rocketride.chat_criteria(prompt)
        if not answer:
            return self._default_viability()
        return self._parse_viability_json(answer)

    # ------------------------------------------------------------------
    # Comment analysis
    # ------------------------------------------------------------------

    async def analyze_comments(
        self,
        pr_data: Dict[str, Any],
        comments: List[Dict[str, Any]],
        diff: str = "",
    ) -> List[Dict[str, Any]]:
        """Analyze which PR comments have been addressed in the current code."""
        if not comments:
            return []

        comments_text = "\n\n".join(
            f"Comment by @{c.get('author', 'unknown')}"
            f"{' on ' + c.get('path', '') if c.get('path') else ''}:\n"
            f"{c.get('body', '')[:500]}"
            for c in comments[:20]
        )

        prompt = (
            f"{COMMENT_ANALYSIS_PROMPT}\n\n"
            f"PR #{pr_data.get('number')} — {pr_data.get('title', '')}\n\n"
            f"=== REVIEW COMMENTS ===\n{comments_text}\n\n"
            f"=== CURRENT DIFF ===\n{diff[:4000]}"
        )

        answer = await rocketride.chat(prompt)
        if not answer:
            return []
        return self._parse_comment_analysis(answer)

    # ------------------------------------------------------------------
    # Ticket / issue evaluation
    # ------------------------------------------------------------------

    async def evaluate_ticket(
        self,
        pr_data: Dict[str, Any],
        ticket: Optional[Dict[str, Any]],
        diff: str = "",
    ) -> Dict[str, Any]:
        """Evaluate whether the linked ticket makes sense and if the PR implements it correctly."""
        if not ticket:
            return {
                "ticket_makes_sense": True,
                "implementation_matches_ticket": True,
                "is_redundant": False,
                "is_counterproductive": False,
                "risk_level": "low",
                "risk_reasons": [],
                "ticket_assessment": "No linked ticket found.",
                "implementation_assessment": "Cannot assess without a ticket.",
                "needs_human_review": False,
                "human_review_reason": "",
            }

        ticket_comments_str = "\n".join(
            f"  @{c.get('author', '?')}: {c.get('body', '')[:200]}"
            for c in ticket.get("comments", [])[:5]
        )

        prompt = (
            f"{TICKET_EVALUATION_PROMPT}\n\n"
            f"=== TICKET/ISSUE #{ticket.get('number')} ===\n"
            f"Title: {ticket.get('title', '')}\n"
            f"Labels: {', '.join(ticket.get('labels', []))}\n"
            f"Body:\n{ticket.get('body', '')[:2000]}\n"
            f"Discussion:\n{ticket_comments_str}\n\n"
            f"=== PR #{pr_data.get('number')} ===\n"
            f"Title: {pr_data.get('title', '')}\n"
            f"Description: {(pr_data.get('description') or '')[:1000]}\n"
            f"Files changed: {', '.join((pr_data.get('filesChanged') or pr_data.get('files_changed') or [])[:20])}\n\n"
            f"=== DIFF (excerpt) ===\n{diff[:3000]}"
        )

        answer = await rocketride.chat(prompt)
        if not answer:
            return {
                "ticket_makes_sense": True,
                "implementation_matches_ticket": True,
                "is_redundant": False,
                "is_counterproductive": False,
                "risk_level": "medium",
                "risk_reasons": ["Could not evaluate ticket — LLM unavailable"],
                "ticket_assessment": "Evaluation unavailable.",
                "implementation_assessment": "Evaluation unavailable.",
                "needs_human_review": True,
                "human_review_reason": "Automated evaluation failed — please review manually.",
            }
        return self._parse_ticket_evaluation(answer)

    # ------------------------------------------------------------------
    # Review generation (personalized opinion, not editable)
    # ------------------------------------------------------------------

    async def generate_review(
        self,
        pr_data: Dict[str, Any],
        viability: Dict[str, Any],
        comment_analysis: List[Dict[str, Any]],
        ticket_eval: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a personalized AI opinion as a review comment."""
        comments_status = "\n".join(
            f"- @{c.get('author', '?')}: \"{c.get('body', '')[:80]}...\" → {c.get('status', 'unknown')}: {c.get('explanation', '')}"
            for c in comment_analysis
        ) if comment_analysis else "No previous comments found."

        ticket_section = ""
        if ticket_eval and ticket_eval.get("ticket_assessment") != "No linked ticket found.":
            ticket_section = (
                f"\n=== TICKET EVALUATION ===\n"
                f"Ticket makes sense: {ticket_eval.get('ticket_makes_sense', '?')}\n"
                f"Implementation matches ticket: {ticket_eval.get('implementation_matches_ticket', '?')}\n"
                f"Is redundant: {ticket_eval.get('is_redundant', '?')}\n"
                f"Is counterproductive: {ticket_eval.get('is_counterproductive', '?')}\n"
                f"Ticket assessment: {ticket_eval.get('ticket_assessment', '')}\n"
                f"Implementation assessment: {ticket_eval.get('implementation_assessment', '')}\n"
            )

        prompt = (
            f"{REVIEW_GENERATION_PROMPT}\n\n"
            f"PR #{pr_data.get('number')} — {pr_data.get('title', '')}\n"
            f"Author: {pr_data.get('author', '')}\n"
            f"Description: {(pr_data.get('description') or '')[:1000]}\n\n"
            f"=== VIABILITY ASSESSMENT ===\n"
            f"Score: {viability.get('viability_score', 0)}/100\n"
            f"Strengths: {', '.join(viability.get('strengths', []))}\n"
            f"Weaknesses: {', '.join(viability.get('weaknesses', []))}\n"
            f"Recommendations: {', '.join(viability.get('recommendations', []))}\n\n"
            f"=== COMMENT ANALYSIS ===\n{comments_status}"
            f"{ticket_section}"
        )

        answer = await rocketride.chat(prompt)
        if not answer:
            return {
                "body": "Unable to generate review.",
                "event": "COMMENT",
                "risk_level": "medium",
                "needs_human_review": True,
                "human_review_reason": "Automated review generation failed.",
            }
        return self._parse_review_json(answer)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _default_viability(self) -> Dict[str, Any]:
        return {
            "viability_score": 0,
            "strengths": [],
            "weaknesses": ["Criteria not yet ingested — run criteria ingestion first"],
            "recommendations": ["Ingest commit criteria before assessing viability"],
            "overall_assessment": "No engineering criteria available for comparison.",
        }

    def _parse_viability_json(self, text: str) -> Dict[str, Any]:
        text = self._strip_json_wrapper(text)
        try:
            data = json.loads(text)
            return {
                "viability_score": max(0, min(100, int(data.get("viability_score", 50)))),
                "strengths": data.get("strengths", []),
                "weaknesses": data.get("weaknesses", []),
                "recommendations": data.get("recommendations", []),
                "overall_assessment": data.get("overall_assessment", ""),
            }
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse viability JSON: {text[:300]}")
            return self._default_viability()

    def _parse_comment_analysis(self, text: str) -> List[Dict[str, Any]]:
        text = self._strip_json_wrapper(text)
        try:
            return json.loads(text)
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse comment analysis JSON: {text[:300]}")
            return []

    def _parse_ticket_evaluation(self, text: str) -> Dict[str, Any]:
        text = self._strip_json_wrapper(text)
        try:
            data = json.loads(text)
            return {
                "ticket_makes_sense": data.get("ticket_makes_sense", True),
                "implementation_matches_ticket": data.get("implementation_matches_ticket", True),
                "is_redundant": data.get("is_redundant", False),
                "is_counterproductive": data.get("is_counterproductive", False),
                "risk_level": data.get("risk_level", "medium"),
                "risk_reasons": data.get("risk_reasons", []),
                "ticket_assessment": data.get("ticket_assessment", ""),
                "implementation_assessment": data.get("implementation_assessment", ""),
                "needs_human_review": data.get("needs_human_review", False),
                "human_review_reason": data.get("human_review_reason", ""),
            }
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse ticket evaluation JSON: {text[:300]}")
            return {
                "ticket_makes_sense": True,
                "implementation_matches_ticket": True,
                "is_redundant": False,
                "is_counterproductive": False,
                "risk_level": "medium",
                "risk_reasons": ["Parse error"],
                "ticket_assessment": "Could not evaluate.",
                "implementation_assessment": "Could not evaluate.",
                "needs_human_review": True,
                "human_review_reason": "Automated evaluation returned unparseable results.",
            }

    def _parse_review_json(self, text: str) -> Dict[str, Any]:
        text = self._strip_json_wrapper(text)
        try:
            data = json.loads(text)
            return {
                "body": data.get("body", "Unable to generate review."),
                "event": data.get("event", "COMMENT"),
                "risk_level": data.get("risk_level", "low"),
                "needs_human_review": data.get("needs_human_review", False),
                "human_review_reason": data.get("human_review_reason", ""),
            }
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse review JSON: {text[:300]}")
            return {
                "body": text[:2000],
                "event": "COMMENT",
                "risk_level": "medium",
                "needs_human_review": True,
                "human_review_reason": "Review text could not be parsed as structured JSON.",
            }

    def _strip_json_wrapper(self, text: str) -> str:
        """Strip markdown fences and extract JSON object/array."""
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        # Try object first
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            return text[start:end]
        # Try array
        start = text.find("[")
        end = text.rfind("]") + 1
        if start != -1 and end > start:
            return text[start:end]
        return text

    def _parse_analysis_json(self, text: str) -> Dict[str, Any]:
        text = text.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        # Extract JSON object if embedded in prose
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]
        try:
            data = json.loads(text)
            similar_raw = data.get("similar_prs", [])
            similar_prs = [int(x) for x in similar_raw if str(x).isdigit() or isinstance(x, int)]
            return {
                "topics": data.get("topics", ["other"]),
                "summary": data.get("summary", ""),
                "recommendation": data.get("recommendation", "keep"),
                "score": max(0, min(100, int(data.get("score", 50)))),
                "reasoning": data.get("reasoning", ""),
                "similar_prs": similar_prs,
            }
        except (json.JSONDecodeError, ValueError):
            logger.warning(f"Could not parse analysis JSON: {text[:300]}")
            return self._default_analysis()

    def _default_analysis(self) -> Dict[str, Any]:
        return {
            "topics": ["other"],
            "summary": "Analysis pending",
            "recommendation": "keep",
            "score": 50,
            "reasoning": "Could not complete analysis",
            "similar_prs": [],
        }

