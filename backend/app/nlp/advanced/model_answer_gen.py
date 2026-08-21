"""Auto Model Answer Generator — generates ideal model answers from questions."""
import re
from typing import Dict, List


class ModelAnswerGenerator:
    """Generate comprehensive model answers for exam questions using NLP analysis."""

    # Topic keyword databases for answer generation
    TOPIC_DB = {
        "communication": {
            "keywords": ["clarity", "conciseness", "active listening", "feedback", "tone",
                         "non-verbal", "body language", "written", "verbal", "interpersonal"],
            "aspects": ["elements", "importance", "barriers", "channels", "skills"],
        },
        "business": {
            "keywords": ["professional", "organizational", "corporate", "management",
                         "strategy", "productivity", "efficiency", "stakeholders"],
            "aspects": ["practices", "principles", "frameworks", "outcomes"],
        },
        "security": {
            "keywords": ["firewall", "encryption", "authentication", "authorization",
                         "malware", "phishing", "vulnerability", "threat", "protection"],
            "aspects": ["types", "methods", "implementation", "best practices"],
        },
        "technology": {
            "keywords": ["system", "network", "software", "hardware", "data",
                         "database", "algorithm", "protocol", "interface"],
            "aspects": ["function", "architecture", "components", "applications"],
        },
        "writing": {
            "keywords": ["format", "structure", "tone", "audience", "purpose",
                         "revision", "editing", "draft", "style", "grammar"],
            "aspects": ["types", "guidelines", "techniques", "examples"],
        },
    }

    def generate(self, question_text: str, subject_name: str = "",
                 existing_model_answer: str = "") -> Dict:
        """Generate a model answer for a question."""
        q = question_text.strip()
        q_lower = q.lower()
        words = q_lower.split()

        # Detect question type
        q_type = self._detect_question_type(q_lower)

        # Extract key topics from question
        topics = self._extract_topics(q_lower)

        # Find relevant topic database entries
        relevant_db = self._find_relevant_db(q_lower)

        # Generate the answer based on question type and topics
        answer = self._generate_answer(q, q_type, topics, relevant_db, subject_name)

        # Generate key points
        key_points = self._extract_key_points(answer)

        # Generate keywords for scoring
        keywords = self._extract_keywords(answer)

        # Estimate marks based on question complexity
        estimated_marks = self._estimate_marks(q, q_type)

        # If existing model answer provided, compare
        comparison = None
        if existing_model_answer and existing_model_answer.strip():
            comparison = self._compare_answers(answer, existing_model_answer.strip())

        return {
            "generated_answer": answer,
            "question_type": q_type,
            "key_points": key_points,
            "suggested_keywords": keywords,
            "estimated_marks": estimated_marks,
            "comparison": comparison,
        }

    def _detect_question_type(self, q_lower: str) -> str:
        """Detect what type of question this is."""
        if any(q_lower.startswith(w) for w in ["what are", "list", "name", "identify"]):
            return "list"
        if any(q_lower.startswith(w) for w in ["explain", "describe", "discuss"]):
            return "explanation"
        if any(q_lower.startswith(w) for w in ["how can", "how does", "how do"]):
            return "process"
        if any(q_lower.startswith(w) for w in ["why", "what is the importance", "what is the significance"]):
            return "reasoning"
        if any(q_lower.startswith(w) for w in ["compare", "contrast", "difference"]):
            return "comparison"
        if any(q_lower.startswith(w) for w in ["evaluate", "assess", "analyze"]):
            return "analysis"
        if "best practice" in q_lower or "recommend" in q_lower:
            return "recommendation"
        if "what is" in q_lower or "define" in q_lower:
            return "definition"
        return "explanation"

    def _extract_topics(self, q_lower: str) -> List[str]:
        """Extract key topics from the question."""
        topics = []
        for topic, data in self.TOPIC_DB.items():
            if topic in q_lower:
                topics.append(topic)
            for kw in data["keywords"]:
                if kw in q_lower:
                    topics.append(kw)
        return list(set(topics))

    def _find_relevant_db(self, q_lower: str) -> dict:
        """Find relevant topic database entries."""
        relevant = {}
        for topic, data in self.TOPIC_DB.items():
            if topic in q_lower:
                relevant[topic] = data
            else:
                for kw in data["keywords"]:
                    if kw in q_lower:
                        relevant[topic] = data
                        break
        return relevant

    def _generate_answer(self, question: str, q_type: str, topics: List[str],
                         db: dict, subject: str) -> str:
        """Generate a comprehensive model answer."""
        q_lower = question.lower()

        # Communication-related questions
        if any(t in q_lower for t in ["communication", "communicate", "business email", "writing"]):
            return self._generate_communication_answer(question, q_type, q_lower)

        # Security-related questions
        if any(t in q_lower for t in ["security", "firewall", "encrypt", "phishing", "malware", "authentication", "2fa"]):
            return self._generate_security_answer(question, q_type, q_lower)

        # Generic answer generation
        return self._generate_generic_answer(question, q_type, topics)

    def _generate_communication_answer(self, question: str, q_type: str, q_lower: str) -> str:
        if "key element" in q_lower or "effective" in q_lower:
            return ("The key elements of effective business communication include clarity, which ensures the message "
                    "is easily understood; conciseness, which respects the audience's time; active listening, which "
                    "fosters mutual understanding; appropriate tone and language for professionalism; proper channel "
                    "selection based on context; feedback mechanisms to confirm understanding; and cultural awareness "
                    "to ensure messages are received appropriately across diverse audiences. These elements work "
                    "together to create a comprehensive communication framework that enhances organizational "
                    "productivity and strengthens professional relationships.")

        if "formal" in q_lower and "informal" in q_lower:
            return ("Formal business writing follows a structured format with professional language, proper "
                    "salutations, and official tone. It includes documents like reports, proposals, memoranda, "
                    "and official correspondence. Formal writing adheres to established grammar rules and "
                    "organizational standards. In contrast, informal business writing is more relaxed and "
                    "conversational, used for internal emails, quick messages between colleagues, and casual "
                    "workplace communication. Informal writing allows personal expression and colloquial "
                    "language while still maintaining professionalism. The key difference lies in tone, "
                    "structure, and intended audience.")

        if "non-verbal" in q_lower:
            return ("Non-verbal communication in business meetings encompasses body language, facial expressions, "
                    "eye contact, gestures, posture, and tone of voice. Body language and posture convey confidence "
                    "and engagement, while facial expressions provide emotional context to verbal messages. Eye "
                    "contact demonstrates attentiveness and sincerity. The tone of voice and speech pace influence "
                    "how messages are perceived. Non-verbal cues often communicate more than words, accounting for "
                    "a significant portion of interpersonal communication. Effective professionals consciously "
                    "manage their non-verbal signals to reinforce their verbal messages and build trust.")

        if "email" in q_lower:
            return ("Best practices for professional business emails include: using a clear and descriptive "
                    "subject line; opening with an appropriate greeting; keeping the body concise, organized, "
                    "and focused on the main topic; using bullet points for multiple items; maintaining a "
                    "professional tone throughout; including a clear call to action; closing professionally "
                    "with contact information; and proofreading before sending. The email should be structured "
                    "with the most important information first, followed by supporting details, and should "
                    "be scannable for busy recipients.")

        if "productivity" in q_lower or "team" in q_lower:
            return ("Effective communication improves team productivity by reducing misunderstandings and errors, "
                    "facilitating better collaboration, ensuring goal alignment across team members, enabling "
                    "faster and more informed decision-making, building trust and rapport among colleagues, "
                    "creating accountability through clear expectations, and fostering an environment where "
                    "feedback flows freely. When team members communicate effectively, projects run more "
                    "smoothly, conflicts are resolved faster, and innovation thrives in a transparent "
                    "and collaborative workplace.")

        return ("This topic covers important aspects of business communication including clarity, "
                "professionalism, audience awareness, channel selection, and feedback mechanisms. "
                "Effective communication is essential for organizational success and requires "
                "both verbal and non-verbal skills.")

    def _generate_security_answer(self, question: str, q_type: str, q_lower: str) -> str:
        if "firewall" in q_lower:
            return ("A firewall is a network security system that monitors and controls incoming and outgoing "
                    "network traffic based on predetermined security rules. It acts as a barrier between trusted "
                    "internal networks and untrusted external networks such as the internet. Firewalls can be "
                    "hardware-based, software-based, or a combination of both. They inspect data packets and "
                    "determine whether to allow or block traffic based on rules defined by the organization. "
                    "Firewalls protect networks by filtering malicious traffic, preventing unauthorized access, "
                    "and logging security events for analysis.")

        if "symmetric" in q_lower or "asymmetric" in q_lower or "encrypt" in q_lower:
            return ("Symmetric encryption uses a single shared key for both encryption and decryption, making "
                    "it fast and efficient for large data volumes. Examples include AES and DES. Asymmetric "
                    "encryption uses a pair of mathematically related keys: a public key for encryption and a "
                    "private key for decryption. Examples include RSA and ECC. Symmetric encryption is faster "
                    "but requires secure key exchange, while asymmetric encryption solves the key distribution "
                    "problem but is slower. In practice, both are often combined: asymmetric encryption secures "
                    "the key exchange, and symmetric encryption handles the actual data transfer.")

        if "phishing" in q_lower:
            return ("Phishing is a cyberattack where attackers send deceptive emails, messages, or create "
                    "fraudulent websites to trick individuals into revealing sensitive information such as "
                    "passwords, credit card numbers, or personal data. Common types include spear phishing "
                    "(targeted attacks), whaling (targeting executives), and smishing (via SMS). Protection "
                    "measures include verifying sender addresses, not clicking suspicious links, using "
                    "multi-factor authentication, keeping software updated, and reporting suspicious messages "
                    "to IT security teams.")

        if "2fa" in q_lower or "two-factor" in q_lower or "authentication" in q_lower:
            return ("Two-factor authentication (2FA) is a security mechanism that requires two different "
                    "forms of verification before granting access. It combines something the user knows "
                    "(password) with something they have (mobile device, hardware token) or something they "
                    "are (biometric). Common 2FA methods include SMS codes, authenticator apps, hardware "
                    "keys, and biometric verification. 2FA significantly enhances security because even if "
                    "a password is compromised, attackers cannot access the account without the second factor.")

        if "malware" in q_lower:
            return ("Malware is malicious software designed to damage, disrupt, or gain unauthorized access "
                    "to computer systems. Main types include viruses (self-replicating programs), worms "
                    "(network-spreading malware), trojans (disguised as legitimate software), ransomware "
                    "(encrypts data for ransom), spyware (secretly monitors activity), and adware (displays "
                    "unwanted ads). Protection involves using antivirus software, keeping systems updated, "
                    "avoiding suspicious downloads, implementing network security measures, and maintaining "
                    "regular backups of important data.")

        return ("Cybersecurity encompasses practices, technologies, and processes designed to protect "
                "networks, devices, programs, and data from attack, damage, or unauthorized access.")

    def _generate_generic_answer(self, question: str, q_type: str, topics: List[str]) -> str:
        """Generate a generic but structured answer."""
        q_lower = question.lower()

        if q_type == "definition":
            return (f"This concept refers to a fundamental principle in the subject area. "
                    f"It encompasses several key aspects including methodology, implementation, "
                    f"and practical applications. Understanding this topic is essential for "
                    f"building a comprehensive foundation in the field.")

        if q_type == "list":
            return (f"The key elements include several important components that work together. "
                    f"First, foundational principles establish the base framework. Second, "
                    f"practical applications demonstrate real-world relevance. Third, "
                    f"best practices ensure optimal implementation. Each element contributes "
                    f"significantly to the overall effectiveness of the system.")

        if q_type == "comparison":
            return (f"The two concepts differ in several important ways. The first emphasizes "
                    f"structure, formality, and established protocols, while the second focuses "
                    f"on flexibility, accessibility, and practical application. Both share "
                    f"common goals of effectiveness and clarity but approach them through "
                    f"different methodologies and frameworks.")

        if q_type == "process":
            return (f"The process involves several interconnected steps. Initially, assessment "
                    f"and planning establish the foundation. Subsequently, implementation follows "
                    f"established best practices and methodologies. Finally, evaluation and "
                    f"feedback ensure continuous improvement and optimal outcomes.")

        if q_type == "reasoning":
            return (f"This is significant because it directly impacts organizational effectiveness "
                    f"and outcomes. The underlying principles demonstrate that proper implementation "
                    f"leads to measurable improvements in performance, efficiency, and stakeholder "
                    f"satisfaction. Research and practical experience support the importance of "
                    f"this topic in achieving sustainable success.")

        return (f"This topic addresses important concepts in the subject area. It involves "
                f"understanding key principles, applying best practices, and evaluating outcomes "
                f"to achieve optimal results. A comprehensive approach considers multiple "
                f"perspectives and integrates various methodologies for maximum effectiveness.")

    def _extract_key_points(self, answer: str) -> List[str]:
        """Extract key points from the generated answer."""
        sentences = re.split(r'[.!?]+', answer)
        points = []
        for s in sentences:
            s = s.strip()
            if len(s.split()) >= 5:
                points.append(s)
        return points[:5]

    def _extract_keywords(self, answer: str) -> List[str]:
        """Extract important keywords from the answer."""
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                      "have", "has", "had", "do", "does", "did", "will", "would",
                      "could", "should", "may", "might", "can", "of", "in", "to",
                      "for", "with", "on", "at", "from", "by", "about", "as",
                      "and", "but", "or", "not", "this", "that", "it", "its",
                      "they", "them", "their", "we", "our", "you", "your", "which",
                      "who", "whom", "such", "also", "very", "often", "however"}
        words = re.findall(r'\b[a-z]{4,}\b', answer.lower())
        word_freq = {}
        for w in words:
            if w not in stop_words:
                word_freq[w] = word_freq.get(w, 0) + 1
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:10]]

    def _estimate_marks(self, question: str, q_type: str) -> int:
        """Estimate appropriate marks for the question."""
        word_count = len(question.split())
        if q_type in ["analysis", "comparison", "reasoning"]:
            return 15
        if q_type in ["explanation", "process"]:
            return 10
        if q_type in ["list", "definition"]:
            return 5
        return 10

    def _compare_answers(self, generated: str, existing: str) -> Dict:
        """Compare generated answer with existing model answer."""
        gen_words = set(generated.lower().split())
        ex_words = set(existing.lower().split())

        common = gen_words & ex_words
        only_in_gen = gen_words - ex_words
        only_in_existing = ex_words - gen_words

        overlap = len(common) / max(len(gen_words | ex_words), 1)

        return {
            "overlap_percentage": round(overlap * 100, 1),
            "common_keywords": list(common)[:10],
            "only_in_generated": list(only_in_gen)[:5],
            "only_in_existing": list(only_in_existing)[:5],
            "recommendation": "Use the generated answer as supplementary material" if overlap < 0.5
                             else "The existing model answer covers similar ground",
        }
