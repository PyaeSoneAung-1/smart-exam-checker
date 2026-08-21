"""Seed data for Smart Exam Answer Checker.
Creates demo users, subjects, exams, questions, and sample answers with scores.

Idempotent:
  * Full seed runs only when fewer than 2 students exist.
  * The 3 extra students (San Lin Aung, Swan Yee Htut, Thura Hein) are added
    in a separate, independently-idempotent block so they land on a database
    that was already seeded with the original 2 students too.
"""

import logging
import random
from datetime import datetime, timedelta

from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.models.subject import Subject
from app.models.exam import Exam
from app.models.question import Question
from app.models.answer import StudentAnswer, Score
from app.core.security import get_password_hash

logger = logging.getLogger(__name__)

# Seed passwords
ADMIN_PASSWORD = "123456"
TEACHER_PASSWORD = "123456"
STUDENT_PASSWORD = "123456"

# ─────────────────────────────────────────────────────────────────────────────
# Pre-written sample answers for each of the 10 seeded questions (varied quality)
# Index within each inner list => answer quality (0 = best, 4 = weakest).
# Kept at module scope so both the full seed and the extra-students block can use it.
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_ANSWER_POOL = [
    # Q1 - Business Communication (key elements)
    [
        "Effective business communication requires clarity, conciseness, and professionalism. Key elements include having a clear purpose, understanding your audience, using appropriate tone, organizing your message logically, and maintaining proper grammar. Good communication builds trust and improves workplace productivity.",
        "The key elements of effective business communication are clarity, audience awareness, and professional tone. You need to be clear about your message, know who you are writing for, and maintain a professional style throughout.",
        "Business communication needs clarity and conciseness. You should organize your thoughts, use proper grammar, and consider your audience when writing business messages.",
        "Good business communication is clear and professional. It helps reduce misunderstandings in the workplace.",
        "Business communication requires being clear and professional when talking to colleagues and clients.",
    ],
    # Q2 - Formal vs Informal Business Writing
    [
        "Formal business writing includes reports, proposals, and official correspondence using professional language and structured formats. Informal business writing like emails to colleagues uses conversational tone, contractions, and simpler sentence structures. Formal writing is for external stakeholders and official records, while informal is for internal communication.",
        "Formal business writing uses professional language, complete sentences, and structured formats for reports and proposals. Informal writing uses casual tone for internal emails and quick messages to coworkers.",
        "The main difference is tone and structure. Formal writing is professional and structured, used for reports and official documents. Informal writing is casual and flexible, used for internal emails.",
        "Formal writing is for official documents like reports. Informal writing is for emails to colleagues. Formal uses professional language, informal uses casual tone.",
        "Formal business writing is professional and structured. Informal is casual and used for internal communication.",
    ],
    # Q3 - Non-verbal Communication
    [
        "Non-verbal communication includes body language, facial expressions, gestures, eye contact, and posture. In business meetings, non-verbal cues convey confidence, attentiveness, and professionalism. Maintaining appropriate eye contact shows engagement, while open posture signals approachability.",
        "Non-verbal communication is important in business meetings because it shows confidence and engagement. Eye contact, posture, and facial expressions help build rapport with colleagues and clients.",
        "Body language and non-verbal cues are essential in meetings. They show professionalism and help communicate messages effectively without words.",
        "Non-verbal signals like eye contact and posture matter in business. They show you are engaged and professional.",
        "Non-verbal communication includes gestures and expressions. In meetings, these cues help show confidence and interest.",
    ],
    # Q4 - Professional Business Email
    [
        "Professional business emails should have a clear subject line, appropriate greeting, concise body, and professional closing. Use formal language, avoid jargon, proofread for errors, and include a call to action. Keep paragraphs short and use bullet points for clarity.",
        "Best practices for business emails include clear subject lines, professional greetings, concise content, and proper formatting. Always proofread before sending and include your contact information.",
        "Business emails should be clear and professional. Use proper formatting, formal language, and always proofread before sending.",
        "Professional emails need clear subjects, proper greetings, and concise content. Keep it formal and proofread carefully.",
        "Good business emails are clear, concise, and professional. Use proper formatting and always check for errors.",
    ],
    # Q5 - Communication and Team Productivity
    [
        "Effective communication improves team productivity by reducing misunderstandings, ensuring clear task delegation, and fostering collaboration. Regular team meetings, clear documentation, and open feedback channels help align goals. Active listening and constructive feedback build trust and motivation.",
        "Communication improves productivity by helping teams work together better. Clear instructions, regular meetings, and open feedback help everyone stay aligned and motivated.",
        "Good communication helps teams be more productive. When everyone understands their tasks and can give feedback, work gets done faster and better.",
        "Teams work better when communication is clear. Regular meetings and feedback help everyone stay on track.",
        "Communication helps productivity by reducing confusion and helping teams collaborate effectively.",
    ],
    # Q6 - Firewall
    [
        "A firewall is a network security device or software that monitors and filters incoming and outgoing network traffic based on security rules. It acts as a barrier between trusted internal networks and untrusted external networks like the internet. Firewalls block unauthorized access, prevent malware, and allow legitimate traffic based on predefined policies.",
        "A firewall protects a computer network by monitoring traffic and blocking unauthorized access. It filters incoming and outgoing data based on security rules, acting as a barrier between the internal network and external threats.",
        "Firewalls are security devices that filter network traffic. They block dangerous connections and allow safe traffic based on rules. They protect networks from hackers and malware.",
        "A firewall blocks unauthorized network access. It checks incoming traffic and only allows safe connections based on security rules.",
        "A firewall is a security system that protects networks by filtering traffic and blocking unauthorized access.",
    ],
    # Q7 - Symmetric vs Asymmetric Encryption
    [
        "Symmetric encryption uses the same key for both encryption and decryption, making it faster but requiring secure key sharing. Asymmetric encryption uses a public-private key pair, where the public key encrypts and the private key decrypts. Asymmetric is slower but more secure for key exchange. Common symmetric algorithms include AES, while RSA is a popular asymmetric algorithm.",
        "Symmetric encryption uses one key to encrypt and decrypt data, which is fast but needs secure key exchange. Asymmetric encryption uses two keys - a public key for encryption and a private key for decryption, which is more secure but slower.",
        "The difference is in the keys used. Symmetric uses the same key for both operations. Asymmetric uses different keys - public and private. Symmetric is faster, asymmetric is more secure.",
        "Symmetric encryption uses one shared key. Asymmetric encryption uses a public and private key pair. Symmetric is faster but requires secure key sharing.",
        "Symmetric uses one key, asymmetric uses two keys. Symmetric is faster, asymmetric is more secure for key exchange.",
    ],
    # Q8 - Phishing Attacks
    [
        "Phishing attacks use deceptive emails, messages, or websites to trick users into revealing sensitive information like passwords or credit card numbers. Prevention includes verifying sender addresses, not clicking suspicious links, using anti-phishing software, enabling multi-factor authentication, and educating users about common phishing tactics.",
        "Phishing is a type of cyber attack where criminals send fake emails to steal personal information. You can prevent it by checking sender addresses, avoiding suspicious links, and using two-factor authentication.",
        "Phishing attacks trick people into giving away passwords and personal data. Prevention includes being careful with emails, not clicking unknown links, and using security software.",
        "Phishing uses fake emails to steal information. Always verify senders and avoid clicking suspicious links to stay safe.",
        "Phishing is when attackers send fake messages to steal data. Be careful with emails and use two-factor authentication.",
    ],
    # Q9 - Two-Factor Authentication
    [
        "Two-factor authentication (2FA) adds an extra layer of security by requiring two forms of verification: something you know (password) and something you have (phone, token, or biometric). 2FA protects against password theft, brute force attacks, and unauthorized access. Even if a password is compromised, the second factor prevents unauthorized login.",
        "Two-factor authentication requires two types of verification to log in. It uses your password plus a code from your phone or a biometric scan. This makes accounts much more secure.",
        "2FA adds security by requiring a password and a second verification like a phone code. It protects accounts even if passwords are stolen.",
        "Two-factor authentication uses two things to verify your identity. A password and a code from your phone. It makes accounts more secure.",
        "2FA is extra security that requires a password and a second factor like a phone code to log in.",
    ],
    # Q10 - Types of Malware
    [
        "Malware includes viruses, worms, trojans, ransomware, spyware, and adware. Viruses attach to files and spread when executed. Worms self-replicate across networks. Trojans disguise as legitimate software. Ransomware encrypts files and demands payment. Spyware monitors user activity. Malware can cause data loss, system damage, and financial loss.",
        "Malware is malicious software that includes viruses, worms, trojans, and ransomware. Viruses spread through files, worms through networks, trojans pretend to be legitimate software, and ransomware locks your files until you pay.",
        "Types of malware include viruses, trojans, ransomware, and spyware. Each type damages computers in different ways, from stealing data to locking files.",
        "Malware includes viruses, ransomware, and spyware. They can damage systems, steal data, and cause financial loss.",
        "Malware is bad software like viruses and ransomware. It can harm computers and steal information.",
    ],
]


def _feedback_for(pct: float) -> str:
    if pct >= 80:
        return "🌟 Excellent answer! Outstanding work."
    if pct >= 65:
        return "✅ Very good answer! Well done."
    if pct >= 50:
        return "👍 Good answer, but there's room for improvement."
    if pct >= 35:
        return "📚 Fair answer. Review the key concepts."
    return "⚠️ Needs significant improvement. Study the topic more carefully."


def _create_student_answers(db, student, questions, score_range, base_time):
    """Create StudentAnswer + Score rows for one student across all questions.

    Mirrors the original seeding logic so the extra students are graded the
    same way as the original two.
    """
    sr = score_range
    count = 0
    for q_idx, question in enumerate(questions):
        pool = SAMPLE_ANSWER_POOL[q_idx]
        answer_text = pool[student.id % len(pool)]

        # Plagiarism test: Pyae Myat Phyo copies Pyae Sone Aung's Q#7 answer.
        # (Only relevant for the original students; harmless for the new ones.)
        if student.name == "Pyae Myat Phyo" and q_idx == 6:
            answer_text = (
                "Symmetric encryption uses the same key for both encryption and decryption, "
                "making it faster but requiring secure key sharing. Asymmetric encryption uses "
                "a public-private key pair, where the public key encrypts and the private key "
                "decrypts. Asymmetric is slower but more secure for key exchange. Common symmetric "
                "algorithms include AES, while RSA is a popular asymmetric algorithm."
            )

        submitted = base_time + timedelta(
            days=random.randint(1, 25),
            hours=random.randint(8, 22),
        )

        answer = StudentAnswer(
            question_id=question.id,
            student_id=student.id,
            answer_text=answer_text,
            submitted_at=submitted,
        )
        db.add(answer)
        db.flush()

        keyword_base = random.uniform(sr[0], sr[1])
        similarity_base = random.uniform(sr[2], sr[3])
        grammar_base = random.uniform(sr[4], sr[5])
        completeness_base = random.uniform(sr[6], sr[7])

        weighted = (
            keyword_base * 0.30
            + similarity_base * 0.40
            + grammar_base * 0.15
            + completeness_base * 0.15
        )
        total = round(weighted * question.marks, 2)

        score = Score(
            answer_id=answer.id,
            keyword_score=round(keyword_base, 4),
            similarity_score=round(similarity_base, 4),
            grammar_score=round(grammar_base, 4),
            completeness_score=round(completeness_base, 4),
            total_score=total,
            feedback=_feedback_for((total / question.marks) * 100),
            is_overridden=False,
        )
        db.add(score)
        count += 1
    return count


# Score ranges per student profile (keyword hi/lo, similarity hi/lo, grammar hi/lo, completeness hi/lo)
SCORE_RANGES = {
    "high": (0.7, 0.95, 0.65, 0.9, 0.8, 0.98, 0.6, 0.85),
    "medium": (0.3, 0.6, 0.25, 0.55, 0.5, 0.75, 0.3, 0.55),
    "medium_low": (0.4, 0.7, 0.35, 0.65, 0.55, 0.8, 0.4, 0.65),
    "low": (0.2, 0.5, 0.15, 0.45, 0.4, 0.65, 0.2, 0.45),
}




# ─────────────────────────────────────────────────────────────────────
# New: 3 extra teachers (Daw Aye Thidar Win, Daw Zin Thu Thu Myint, Daw Tar
# Tar Khin) with subjects, midterm exams, questions and pre-graded answers.
# ─────────────────────────────────────────────────────────────────────
NEW_TEACHERS = [
    ("Daw Aye Thidar Win", "dawayethidarwin@gmail.com"),
    ("Daw Zin Thu Thu Myint", "dawzinthuthumyint@gmail.com"),
    ("Daw Tar Tar Khin", "dawtartarkhin@gmail.com"),
]

NEW_SUBJECTS = [
    ("Natural Language Processing", "Understanding human language with machines: tokenization, embeddings, and language models.", "dawayethidarwin@gmail.com"),
    ("Data Mining", "Discovering patterns and knowledge from large datasets: classification, clustering, and association.", "dawzinthuthumyint@gmail.com"),
    ("Enterprise Resource Planning", "Integrated management of core business processes: finance, HR, supply chain, and ERP implementation.", "dawtartarkhin@gmail.com"),
]

NEW_EXAMS = [
    ("NLP Midterm Exam", "Core concepts of Natural Language Processing.", "Natural Language Processing"),
    ("Data Mining Midterm Exam", "Core concepts of Data Mining.", "Data Mining"),
    ("ERP Midterm Exam", "Core concepts of Enterprise Resource Planning.", "Enterprise Resource Planning"),
]

NEW_QUESTIONS = [
    ("Natural Language Processing", "What is natural language processing (NLP) and what are its main applications?", "Natural language processing (NLP) is a field of artificial intelligence that enables computers to understand, interpret, and generate human language. Its main applications include machine translation, sentiment analysis, chatbots, speech recognition, text summarization, and information extraction. NLP combines linguistics, computer science, and machine learning to process unstructured text data.", ["natural language processing", "artificial intelligence", "machine translation", "sentiment analysis", "chatbots", "text"]),
    ("Natural Language Processing", "Explain the difference between stemming and lemmatization.", "Stemming and lemmatization are both text normalization techniques used in NLP. Stemming removes word suffixes heuristically to produce a base form, which may not be a real word (for example, 'running' becomes 'run' but 'flies' becomes 'fli'). Lemmatization uses vocabulary and morphological analysis to return the dictionary base form, called a lemma, so 'running' becomes 'run' and 'flies' becomes 'fly'. Lemmatization is more accurate but slower and needs a lexicon, while stemming is faster but can produce non-words.", ["stemming", "lemmatization", "normalization", "base form", "lemma", "morphological"]),
    ("Natural Language Processing", "What is a bag-of-words model and what are its limitations?", "Bag-of-words is a text representation that turns a document into a multiset of word counts, ignoring grammar and word order. Each document becomes a vector of word frequencies. Its limitations include losing word order and semantics, very high and sparse dimensionality, and failing to handle synonyms, since words with similar meanings get completely different vectors. Weighting schemes like TF-IDF and dense word embeddings are used to address some of these problems.", ["bag-of-words", "vector", "word order", "semantics", "dimensionality", "tf-idf"]),
    ("Natural Language Processing", "Describe how a transformer-based language model works at a high level.", "A transformer is a neural network architecture based on self-attention. Input tokens are first converted into embeddings, then self-attention computes weighted relationships between every pair of tokens in parallel, allowing the model to capture context. Multi-head attention, positional encodings, and feed-forward layers form the encoder and decoder blocks. Models are pretrained on large text corpora using objectives like masked language modeling, and then fine-tuned for downstream tasks.", ["transformer", "self-attention", "embeddings", "context", "pretraining", "positional encoding"]),
    ("Natural Language Processing", "What is the difference between supervised and unsupervised learning in NLP?", "In supervised NLP, models are trained on labeled data, such as sentiment labels or part-of-speech tags, so they learn to predict an output for new inputs. In unsupervised learning, models discover structure in unlabeled text, such as topic modeling with LDA or word embeddings like Word2Vec trained on raw corpora. Supervised learning is task-specific and needs labeled datasets, while unsupervised learning finds patterns without any labels.", ["supervised", "unsupervised", "labeled", "topic modeling", "word2vec", "word embeddings"]),
    ("Data Mining", "What is data mining and what are its main tasks?", "Data mining is the process of discovering patterns, correlations, and useful knowledge from large datasets using techniques from statistics, machine learning, and database systems. Its main tasks include classification, clustering, regression, association rule mining, anomaly detection, and prediction. Common applications are customer segmentation, fraud detection, and market basket analysis.", ["data mining", "patterns", "classification", "clustering", "association", "prediction"]),
    ("Data Mining", "Explain the difference between classification and clustering.", "Classification is a supervised learning task in which data items are assigned to predefined classes using a labeled training set, for example classifying emails as spam or not spam. Clustering is an unsupervised task that groups similar data points together without any prior labels, for example segmenting customers by behavior. Classification predicts known labels, while clustering discovers unknown groups in the data.", ["classification", "clustering", "supervised", "unsupervised", "labels", "groups"]),
    ("Data Mining", "What is association rule mining and how are support and confidence computed?", "Association rule mining discovers relationships between items in transaction data, such as the market basket rule that customers who buy bread also buy butter. For a rule X implies Y, support is the fraction of transactions that contain both X and Y, and confidence is the fraction of transactions containing X that also contain Y. Lift measures how much more likely Y is when X is present compared to when it is not.", ["association rule", "support", "confidence", "market basket", "lift", "transactions"]),
    ("Data Mining", "Describe the k-means clustering algorithm and its limitations.", "K-means partitions data into k clusters by minimizing the within-cluster variance. It starts by choosing k initial centroids, assigns every point to the nearest centroid, recomputes each centroid as the mean of its points, and repeats until convergence. Its limitations are that k must be chosen in advance, results are sensitive to initialization and outliers, it assumes spherical clusters of similar size, and it can converge to local optima.", ["k-means", "centroid", "variance", "k", "outliers", "convergence"]),
    ("Data Mining", "What is the difference between training data and test data, and why is it important?", "Training data is used to fit the parameters of a model, while test data evaluates the model on unseen examples to measure how well it generalizes. Keeping them separate prevents overfitting, where a model memorizes the training data but performs poorly on new data. Techniques such as holdout validation and cross-validation give more reliable estimates of real-world performance.", ["training", "test", "generalization", "overfitting", "cross-validation", "unseen"]),
    ("Enterprise Resource Planning", "What is an ERP system and what are its main benefits?", "An ERP system is integrated software that manages the core business processes of an organization, including finance, human resources, procurement, manufacturing, sales, and inventory, all sharing a single unified database. Its main benefits are real-time visibility of data, automation of processes, reduced data duplication, better decision making, and streamlined workflows across departments.", ["ERP", "integrated", "database", "finance", "inventory", "automation"]),
    ("Enterprise Resource Planning", "Explain the difference between on-premise and cloud ERP.", "On-premise ERP is installed on the company's own servers, giving full control and data ownership, but it requires high upfront costs and in-house IT staff for maintenance. Cloud ERP, usually delivered as SaaS, is hosted by the vendor and accessed over the internet, with lower upfront cost, automatic updates, and easy scalability, but it depends on internet connectivity and vendor security practices.", ["on-premise", "cloud", "saas", "upfront cost", "scalability", "vendor"]),
    ("Enterprise Resource Planning", "What is master data in an ERP system and why is it important?", "Master data is the core reference data shared across an organization, such as customers, vendors, products, employees, and the chart of accounts. It is important because it provides a single source of truth, so every module uses consistent and accurate information. Master data management (MDM) maintains the quality, consistency, and governance of this data across the system.", ["master data", "single source of truth", "customers", "products", "governance", "mdm"]),
    ("Enterprise Resource Planning", "Describe the main modules typically found in an ERP system.", "Typical ERP modules include finance and accounting, human resources, procurement, inventory and supply chain management, manufacturing or production, sales and distribution, and customer relationship management (CRM). Because all modules share one database, a transaction in one area automatically updates others, for example a sales order reducing inventory and updating the finance ledger.", ["finance", "human resources", "procurement", "inventory", "supply chain", "crm"]),
    ("Enterprise Resource Planning", "What are the key steps in an ERP implementation project?", "Key steps in an ERP implementation are requirements analysis, selection of the ERP package and vendor, project planning, system design and configuration, data migration, integration with existing systems, testing, user training, go-live, and post-implementation support. Change management and strong executive sponsorship are critical to the success of the project.", ["requirements", "configuration", "data migration", "testing", "training", "go-live"]),
]

NEW_ANSWER_POOL = [
    ("What is natural language processing (NLP) and what are its main applications?", ["Natural language processing, or NLP, is a branch of artificial intelligence that lets computers understand, interpret, and generate human language. Main applications are machine translation, sentiment analysis, chatbots, speech recognition, and text summarization. It brings together linguistics, computer science, and machine learning to work with unstructured text.", "NLP is a field of AI that helps computers understand human language. Applications include translation, sentiment analysis, chatbots, and speech recognition. It combines linguistics and machine learning.", "NLP is an AI field focused on getting computers to understand and produce human language. It powers machine translation, sentiment analysis, chatbots, speech recognition, and text summarization by combining linguistics with machine learning.", "NLP is about computers understanding human language, like in translation and chatbots.", "NLP helps computers read and understand human language. It is used in translation, chatbots and speech recognition."]),
    ("Explain the difference between stemming and lemmatization.", ["Stemming and lemmatization both normalize words to their base form. Stemming strips suffixes with simple rules, so it is fast but can create non-words like 'fli' from 'flies'. Lemmatization uses vocabulary and morphological analysis to return the real dictionary form (the lemma), such as 'fly' from 'flies'. Lemmatization is more accurate but slower and requires a lexicon; stemming is quicker but less precise.", "Stemming removes suffixes from words to get a base form, while lemmatization returns the true dictionary form using vocabulary and morphology. Lemmatization is more accurate but slower.", "Both techniques reduce words to simpler forms. Stemming chops off endings with quick rules, sometimes producing non-words. Lemmatization looks words up in a dictionary to return their proper base form, so it is more accurate but needs more processing.", "Stemming and lemmatization both reduce words to base forms. Lemmatization is more accurate than stemming.", "Stemming cuts word endings quickly, lemmatization finds the real base word, so lemmatization is more correct."]),
    ("What is a bag-of-words model and what are its limitations?", ["The bag-of-words model represents text as a collection of word counts without considering grammar or word order, so each document becomes a frequency vector. Its main limitations are that it loses word order and meaning, produces high-dimensional and sparse vectors, and cannot recognize synonyms, because similar words map to different dimensions. TF-IDF weighting and word embeddings help overcome some of these issues.", "Bag-of-words counts word frequencies in a document and ignores grammar and word order. It loses semantics and creates large sparse vectors, and it cannot handle synonyms well.", "Bag-of-words turns a document into a list of word counts, with no regard for word order. Because of that it loses meaning, produces very large and sparse vectors, and treats synonyms as unrelated words, which TF-IDF and word embeddings try to fix.", "Bag-of-words counts how often words appear, ignoring order, and it cannot capture meaning or synonyms.", "Bag-of-words counts words without order, so it loses meaning and cannot handle synonyms."]),
    ("Describe how a transformer-based language model works at a high level.", ["A transformer uses self-attention to process text. Tokens are converted to embeddings, and attention layers compute how every token relates to all others in parallel, capturing context. Multi-head attention, positional encodings, and feed-forward layers make up the encoder-decoder blocks. The model is pretrained on huge text corpora with objectives like masked language modeling, then fine-tuned for specific tasks.", "Transformers use self-attention to relate every token to every other token, capturing context in parallel. They are pretrained on large text and fine-tuned for tasks like translation and classification.", "Transformers rely on self-attention: each word looks at every other word to understand context. Words become embeddings, attention layers weigh their relationships, and the network is pretrained on large text corpora before being fine-tuned for specific jobs like translation.", "A transformer is a model that uses attention to understand context in text and is trained on large amounts of data.", "Transformers use attention to connect words and understand context, then get trained on lots of text."]),
    ("What is the difference between supervised and unsupervised learning in NLP?", ["Supervised learning in NLP trains models on labeled data, such as sentiment or part-of-speech labels, to predict outputs for new examples. Unsupervised learning finds structure in unlabeled text, for example topic modeling with LDA or word embeddings such as Word2Vec. Supervised methods are task-specific and require labeled datasets, while unsupervised methods discover patterns without labels.", "Supervised NLP uses labeled data to train models for tasks like sentiment analysis, while unsupervised NLP finds patterns in unlabeled text, like topics or word embeddings.", "Supervised learning trains on labelled examples, such as reviews marked as positive or negative, so the model learns to predict labels for new text. Unsupervised learning works on raw unlabelled text and finds patterns itself, like grouping documents into topics or learning word embeddings.", "Supervised learning uses labeled data; unsupervised learning works without labels.", "Supervised learning needs labelled data, unsupervised learning finds patterns in unlabelled text."]),
    ("What is data mining and what are its main tasks?", ["Data mining is the process of discovering patterns, correlations, and useful knowledge from large datasets using statistics, machine learning, and database techniques. The main tasks are classification, clustering, regression, association rule mining, anomaly detection, and prediction. It is widely used for customer segmentation, fraud detection, and market basket analysis.", "Data mining finds patterns in large datasets using statistics and machine learning. Main tasks include classification, clustering, and association rule mining, used in applications like fraud detection.", "Data mining extracts useful patterns and knowledge from large datasets using statistics, machine learning and databases. Its main jobs are classification, clustering, regression, association rule mining and anomaly detection, applied in areas like fraud detection and customer segmentation.", "Data mining is finding patterns in data, like grouping customers or detecting fraud.", "Data mining finds useful patterns in large data sets, using tasks like classification and clustering."]),
    ("Explain the difference between classification and clustering.", ["Classification is a supervised task where each data item is assigned to predefined classes using a labeled training set, such as spam detection. Clustering is an unsupervised task that groups similar items together without labels, such as customer segmentation. In short, classification predicts known labels, while clustering discovers unknown groups.", "Classification assigns data to known classes using labeled examples, while clustering groups similar data without labels. Classification is supervised; clustering is unsupervised.", "Classification assigns items to fixed classes using labelled training data, for example deciding whether an email is spam. Clustering groups similar items on its own without labels, such as dividing customers into segments based on behaviour.", "Classification puts data into known groups; clustering finds groups by itself.", "Classification sorts data into known classes, clustering groups data by similarity without labels."]),
    ("What is association rule mining and how are support and confidence computed?", ["Association rule mining finds relationships between items in transaction data, like market basket analysis. For a rule X implies Y, support is the fraction of transactions containing both X and Y, while confidence is the fraction of transactions with X that also contain Y. Lift compares how much more likely Y is when X is present.", "Association rule mining finds item relationships in transactions, like bread and butter. Support is the frequency of both items together, and confidence is how often Y appears when X appears.", "Association mining looks for rules among items in transactions, like bread and butter being bought together. Support is the share of transactions that contain both items, and confidence is the share of transactions with the first item that also have the second. Lift compares this to random chance.", "Association rules find items often bought together. Support and confidence measure how strong the rule is.", "Association mining finds items often bought together. Support is how often both appear, confidence is how often the second follows the first."]),
    ("Describe the k-means clustering algorithm and its limitations.", ["K-means partitions data into k clusters by minimizing within-cluster variance. It initializes k centroids, assigns each point to the nearest centroid, recalculates centroids as the mean of their points, and repeats until convergence. Limitations include having to choose k in advance, sensitivity to initialization and outliers, assuming spherical clusters, and the risk of local optima.", "K-means groups data into k clusters using centroids and repeated assignments. Its limits are needing k in advance and being sensitive to outliers and initialization.", "K-means splits data into k clusters by minimising the distance of points from their cluster centre. It picks k starting centres, assigns points to the nearest one, updates the centres as averages, and repeats. The user must choose k, and results depend on the starting centres and can be affected by outliers.", "K-means clusters data into k groups. You must choose k and outliers can affect the result.", "K-means puts data into k groups around centres. You have to pick k, and outliers can skew the result."]),
    ("What is the difference between training data and test data, and why is it important?", ["Training data is used to fit a model's parameters, and test data measures performance on unseen examples to check generalization. Separating the two prevents overfitting, where the model memorizes training data but fails on new data. Holdout sets and cross-validation provide more reliable performance estimates.", "Training data fits the model and test data checks it on new examples. This separation prevents overfitting and shows how well the model generalizes.", "Training data fits the model parameters, while test data checks performance on examples the model has never seen. Keeping them separate stops overfitting, where the model memorises training examples but fails on new data, and cross-validation gives a more honest estimate of performance.", "Training data trains the model and test data checks if it works on new data.", "Training data teaches the model and test data checks it on new examples, which prevents overfitting."]),
    ("What is an ERP system and what are its main benefits?", ["An ERP system is integrated software that manages core business processes such as finance, human resources, procurement, manufacturing, sales, and inventory in one unified database. The main benefits are real-time data visibility, process automation, less data duplication, better decision making, and smoother workflows across departments.", "ERP is software that integrates business processes like finance, HR, and inventory into one system. Benefits include real-time data, automation, and better decisions.", "ERP is a single integrated software suite that handles core business functions such as finance, HR, purchasing, production, sales and stock, all on one shared database. It gives real-time information, automates routine tasks, removes duplicate data and supports better decisions across the whole company.", "ERP is a system that connects company departments together using one database.", "ERP is one software system for finance, HR, sales and stock, giving real-time data and fewer duplicate records."]),
    ("Explain the difference between on-premise and cloud ERP.", ["On-premise ERP runs on the company's own servers, giving full control and data ownership but requiring high upfront cost and in-house IT maintenance. Cloud ERP is hosted by the vendor as SaaS and accessed over the internet, offering lower upfront cost, automatic updates, and scalability, but relying on connectivity and vendor security.", "On-premise ERP is installed on company servers with high upfront cost, while cloud ERP is hosted by the vendor with lower cost and easier scaling.", "On-premise ERP runs on company-owned servers, so the firm has full control and owns the data, but it pays high upfront costs and must maintain its own IT team. Cloud ERP is hosted by the vendor as a service, costs less upfront, updates automatically and scales easily, though it depends on the internet and the vendor's security.", "On-premise ERP runs on your own servers; cloud ERP runs on the vendor's servers.", "On-premise ERP runs on your own servers and costs more upfront, while cloud ERP is hosted by the vendor and costs less."]),
    ("What is master data in an ERP system and why is it important?", ["Master data is the core reference data shared across the organization, such as customers, vendors, products, employees, and the chart of accounts. It matters because it creates a single source of truth, ensuring all modules use consistent information. Master data management (MDM) keeps this data accurate, consistent, and properly governed.", "Master data is shared reference data like customers and products. It gives the organization a single source of truth so all modules use the same information.", "Master data is the key reference information shared across the business, such as customer, supplier, product and employee records. It matters because it creates one trusted source of truth, so every module uses the same correct data, and master data management keeps that data accurate and consistent.", "Master data is the important shared data like customer and product lists used across the system.", "Master data is shared reference data like customer and product records, giving one reliable source of truth."]),
    ("Describe the main modules typically found in an ERP system.", ["Typical ERP modules are finance and accounting, human resources, procurement, inventory and supply chain, manufacturing, sales and distribution, and customer relationship management (CRM). All modules share a single database, so a transaction like a sales order automatically updates inventory and finance records.", "ERP modules include finance, HR, procurement, inventory, sales, and CRM. They share one database so data flows between departments automatically.", "ERP systems usually include modules for finance and accounting, human resources, purchasing, inventory and supply chain, manufacturing, sales and customer relationship management. Since everything shares one database, a sale automatically updates stock levels and the financial records.", "ERP has modules for finance, HR, inventory, and sales that work together.", "ERP modules cover finance, HR, purchasing, inventory, sales and CRM, all sharing one database."]),
    ("What are the key steps in an ERP implementation project?", ["The key steps are requirements analysis, vendor and package selection, planning, configuration, data migration, integration, testing, training, go-live, and post-implementation support. Change management and executive sponsorship are critical for success.", "An ERP project goes through requirements, configuration, data migration, testing, training, and go-live. Good change management is important.", "An ERP project starts with analysing requirements and choosing the software and vendor, then planning, configuring the system, migrating data, testing, training users, going live and providing ongoing support. Managing the change for staff and having strong leadership support are essential for success.", "ERP implementation includes planning, setup, testing, training, and going live.", "ERP implementation involves planning, setup, data migration, testing, training and going live, with good change management."]),
]

NEW_STUDENT_LEVELS = {
    # student email -> answer index in NEW_ANSWER_POOL
    # 0=excellent, 1=good, 2=good (variant), 3=weak, 4=weak (variant)
    "sanlinaung@gmail.com": 0,
    "pyaesoneaung@gmail.com": 1,
    "swanyeehtut@gmail.com": 2,
    "pyaemyatphyo@gmail.com": 3,
    "thurahein@gmail.com": 4,
}


def _seed_new_exams(db):
    """Add 3 teachers, 3 subjects, 3 exams, 15 questions and pre-graded student
    answers for the new exams (idempotent — safe on every startup)."""
    # 1. Teachers
    teacher_by_email = {}
    for name, email in NEW_TEACHERS:
        t = db.query(User).filter(User.email == email).first()
        if not t:
            t = User(name=name, email=email,
                     hashed_password=get_password_hash(TEACHER_PASSWORD),
                     role=UserRole.TEACHER, is_active=True)
            db.add(t)
            db.flush()
        teacher_by_email[email] = t

    # 2. Subjects
    subject_by_name = {}
    for name, desc, teacher_email in NEW_SUBJECTS:
        s = db.query(Subject).filter(Subject.name == name).first()
        if not s:
            s = Subject(name=name, description=desc,
                        teacher_id=teacher_by_email[teacher_email].id)
            db.add(s)
            db.flush()
        subject_by_name[name] = s

    # 3. Exams (one per new subject)
    exam_by_subject = {}
    for title, desc, subj_name in NEW_EXAMS:
        e = db.query(Exam).filter(Exam.title == title).first()
        if not e:
            e = Exam(subject_id=subject_by_name[subj_name].id, title=title,
                     description=desc, total_marks=50.0,
                     time_limit_minutes=60, is_active=True,
                     created_at=datetime.utcnow() - timedelta(days=14))
            db.add(e)
            db.flush()
        exam_by_subject[subj_name] = e

    # 4. Questions (5 per exam, 10 marks each)
    questions_by_text = {}
    for subj_name, qtext, model, keywords in NEW_QUESTIONS:
        q = db.query(Question).filter(Question.question_text == qtext).first()
        if not q:
            q = Question(exam_id=exam_by_subject[subj_name].id,
                         question_text=qtext, model_answer=model,
                         marks=10.0, keywords=keywords)
            db.add(q)
            db.flush()
        questions_by_text[qtext] = q
    db.commit()

    # 5. Students answer all 15 new questions (unique text per student)
    level_ranges = [SCORE_RANGES["high"], SCORE_RANGES["medium"],
                    SCORE_RANGES["medium_low"], SCORE_RANGES["low"],
                    SCORE_RANGES["low"]]
    pool_by_text = dict(NEW_ANSWER_POOL)
    base_time = datetime.utcnow() - timedelta(days=20)
    created = 0
    for email, idx in NEW_STUDENT_LEVELS.items():
        student = (db.query(User)
                   .filter(User.email == email, User.role == UserRole.STUDENT)
                   .first())
        if not student:
            logger.warning(f"  new-exam seed: student {email} not found, skipping.")
            continue
        for qtext, texts in pool_by_text.items():
            q = questions_by_text[qtext]
            existing = (db.query(StudentAnswer)
                        .filter(StudentAnswer.question_id == q.id,
                                StudentAnswer.student_id == student.id)
                        .first())
            if existing:
                continue
            answer = StudentAnswer(question_id=q.id, student_id=student.id,
                                   answer_text=texts[idx],
                                   submitted_at=base_time + timedelta(hours=random.randint(1, 400)))
            db.add(answer)
            db.flush()

            sr = level_ranges[idx]
            keyword_base = random.uniform(sr[0], sr[1])
            similarity_base = random.uniform(sr[2], sr[3])
            grammar_base = random.uniform(sr[4], sr[5])
            completeness_base = random.uniform(sr[6], sr[7])
            weighted = (keyword_base * 0.30 + similarity_base * 0.40
                        + grammar_base * 0.15 + completeness_base * 0.15)
            total = round(weighted * q.marks, 2)
            db.add(Score(answer_id=answer.id,
                         keyword_score=round(keyword_base, 4),
                         similarity_score=round(similarity_base, 4),
                         grammar_score=round(grammar_base, 4),
                         completeness_score=round(completeness_base, 4),
                         total_score=total,
                         feedback=_feedback_for((total / q.marks) * 100),
                         is_overridden=False))
            created += 1

    db.commit()
    logger.info(f"New teachers/subjects/exams seeded: "
                f"{len(NEW_TEACHERS)} teachers, {len(NEW_SUBJECTS)} subjects, "
                f"{len(NEW_EXAMS)} exams, {len(NEW_QUESTIONS)} questions, "
                f"{created} answers")

def seed_data():
    """Seed the database with demo data if it's empty."""
    # Create tables if they don't exist
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if seed data already exists (look for students, not just admin)
        existing_students = db.query(User).filter(User.role == UserRole.STUDENT).count()
        if existing_students >= 2:
            logger.info("Seed data already exists. Skipping full seed.")
        else:
            logger.info("Seeding database with demo data...")

            # ──────────────────────────────────────────────
            # 1. CREATE USERS
            # ──────────────────────────────────────────────
            admin = User(
                name="System Admin",
                email="admin@smartexam.com",
                hashed_password=get_password_hash(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)

            teacher_names = [
                ("Daw Ni Lar Win", "dawnilarwin@gmail.com"),
                ("Daw Nwe Ni Win", "dawnweniwin@gmail.com"),
            ]
            teachers = []
            for name, email in teacher_names:
                t = User(
                    name=name,
                    email=email,
                    hashed_password=get_password_hash(TEACHER_PASSWORD),
                    role=UserRole.TEACHER,
                    is_active=True,
                )
                db.add(t)
                teachers.append(t)

            student_data = [
                ("Pyae Sone Aung", "pyaesoneaung@gmail.com"),
                ("Pyae Myat Phyo", "pyaemyatphyo@gmail.com"),
            ]
            students = []
            for name, email in student_data:
                s = User(
                    name=name,
                    email=email,
                    hashed_password=get_password_hash(STUDENT_PASSWORD),
                    role=UserRole.STUDENT,
                    is_active=True,
                )
                db.add(s)
                students.append(s)

            db.flush()  # Get IDs

            # ──────────────────────────────────────────────
            # 2. CREATE SUBJECTS (2 subjects, 1 per teacher)
            # ──────────────────────────────────────────────
            subject_data = [
                ("E-5101 - Communication in Business English", "Business communication, professional writing, and presentation skills.", teachers[0]),
                ("CS-5121 - Cyber Security", "Network security, cryptography, threat analysis, and defense mechanisms.", teachers[1]),
            ]
            subjects = []
            for name, desc, teacher in subject_data:
                subj = Subject(name=name, description=desc, teacher_id=teacher.id)
                db.add(subj)
                subjects.append(subj)

            db.flush()

            # ──────────────────────────────────────────────
            # 3. CREATE EXAMS (1 per subject = 2 total)
            # ──────────────────────────────────────────────
            base_time = datetime.utcnow() - timedelta(days=30)

            exam_data = [
                (subjects[0], "E-5101 Midterm Exam",
                 "Business communication principles and professional English skills.", 50.0, 60),
                (subjects[1], "CS-5121 Midterm Exam",
                 "Cyber security fundamentals, threats, and defense strategies.", 50.0, 60),
            ]

            exams = []
            for i, (subj, title, desc, marks, time_limit) in enumerate(exam_data):
                exam = Exam(
                    subject_id=subj.id,
                    title=title,
                    description=desc,
                    total_marks=marks,
                    time_limit_minutes=time_limit,
                    is_active=True,
                    created_at=base_time + timedelta(days=i * 3),
                )
                db.add(exam)
                exams.append(exam)

            db.flush()

            # ──────────────────────────────────────────────
            # 4. CREATE QUESTIONS (5 per exam = 10 total)
            # ──────────────────────────────────────────────
            questions_data = [
                # E-5101 Business English - 5 questions (10 marks each = 50 total)
                (exams[0].id, 10.0,
                 "What are the key elements of effective business communication?",
                 "Effective business communication requires clarity, conciseness, and professionalism. Key elements include a clear purpose, audience awareness, appropriate tone, organized structure, and proper grammar. Good business communication builds trust, reduces misunderstandings, and improves productivity in the workplace.",
                 ["clarity", "conciseness", "professionalism", "audience", "tone", "business communication"]),
                (exams[0].id, 10.0,
                 "Explain the difference between formal and informal business writing.",
                 "Formal business writing includes reports, proposals, and official correspondence using professional language and structure. Informal business writing includes internal emails and messages with a more relaxed tone. Formal writing uses complete sentences, avoids slang, and follows specific formatting conventions, while informal writing allows contractions and casual expressions.",
                 ["formal", "informal", "business writing", "professional", "reports", "emails", "tone"]),
                (exams[0].id, 10.0,
                 "Describe the importance of non-verbal communication in business meetings.",
                 "Non-verbal communication includes body language, facial expressions, gestures, eye contact, and posture. In business meetings, non-verbal cues convey confidence, attentiveness, and professionalism. Maintaining appropriate eye contact shows engagement, while open posture signals approachability. Understanding non-verbal communication helps build rapport and avoid misunderstandings.",
                 ["non-verbal", "body language", "facial expressions", "eye contact", "posture", "business meetings"]),
                (exams[0].id, 10.0,
                 "What are the best practices for writing a professional business email?",
                 "Professional business emails should have a clear subject line, appropriate greeting, concise body, and professional closing. Use formal language, avoid jargon, proofread for errors, and include a call to action. Keep paragraphs short, use bullet points for clarity, and respond promptly. Always include your contact information in the signature.",
                 ["email", "professional", "subject line", "greeting", "formal language", "proofread"]),
                (exams[0].id, 10.0,
                 "How can effective communication improve team productivity?",
                 "Effective communication improves team productivity by reducing misunderstandings, ensuring clear task delegation, and fostering collaboration. Regular team meetings, clear documentation, and open feedback channels help align goals. Active listening, constructive feedback, and transparent communication build trust and motivation among team members.",
                 ["communication", "team productivity", "collaboration", "feedback", "active listening", "trust"]),

                # CS-5121 Cyber Security - 5 questions (10 marks each = 50 total)
                (exams[1].id, 10.0,
                 "What is a firewall and how does it protect a computer network?",
                 "A firewall is a network security device or software that monitors and filters incoming and outgoing network traffic based on predetermined security rules. It acts as a barrier between a trusted internal network and untrusted external networks like the internet. Firewalls protect against unauthorized access, malware, and other cyber threats by blocking suspicious traffic.",
                 ["firewall", "network security", "traffic", "filter", "barrier", "unauthorized access", "cyber threats"]),
                (exams[1].id, 10.0,
                 "What is the difference between symmetric and asymmetric encryption?",
                 "Symmetric encryption uses the same key for both encryption and decryption, making it fast but requiring secure key sharing. Asymmetric encryption uses a public key for encryption and a private key for decryption, eliminating the need to share secret keys. Common symmetric algorithms include AES, while RSA is a popular asymmetric algorithm.",
                 ["symmetric", "asymmetric", "encryption", "public key", "private key", "AES", "RSA"]),
                (exams[1].id, 10.0,
                 "Explain the concept of phishing attacks and how to prevent them.",
                 "Phishing attacks use deceptive emails, messages, or websites to trick users into revealing sensitive information like passwords or credit card numbers. Prevention includes verifying sender addresses, not clicking suspicious links, using anti-phishing software, enabling multi-factor authentication, and educating users about common phishing tactics.",
                 ["phishing", "social engineering", "email", "deception", "multi-factor authentication", "prevention"]),
                (exams[1].id, 10.0,
                 "What is two-factor authentication and why is it important?",
                 "Two-factor authentication (2FA) adds an extra layer of security by requiring two forms of verification: something you know (password) and something you have (phone, token, or biometric). 2FA protects against password theft, brute force attacks, and unauthorized access. Even if a password is compromised, the second factor prevents unauthorized login.",
                 ["two-factor", "2FA", "authentication", "security", "verification", "password", "biometric"]),
                (exams[1].id, 10.0,
                 "Describe the main types of malware and their effects on computer systems.",
                 "Malware includes viruses, worms, trojans, ransomware, spyware, and adware. Viruses attach to files and spread when executed. Worms self-replicate across networks. Trojans disguise as legitimate software. Ransomware encrypts files and demands payment. Spyware monitors user activity. Malware can cause data loss, system damage, and financial loss.",
                 ["malware", "virus", "worm", "trojan", "ransomware", "spyware", "data loss"]),
            ]

            all_questions = []
            for exam_id, marks, text, answer, keywords in questions_data:
                q = Question(
                    exam_id=exam_id,
                    question_text=text,
                    model_answer=answer,
                    marks=marks,
                    keywords=keywords,
                )
                db.add(q)
                all_questions.append(q)

            db.flush()

            # ──────────────────────────────────────────────
            # 5. CREATE SAMPLE ANSWERS WITH SCORES
            # Each student answers ALL 10 questions (2 exams × 5 questions)
            # ──────────────────────────────────────────────
            answer_count = 0
            student_profiles = [
                (students[0], SCORE_RANGES["high"]),    # Pyae Sone Aung - HIGH
                (students[1], SCORE_RANGES["medium"]),  # Pyae Myat Phyo - MEDIUM
            ]
            for student, sr in student_profiles:
                answer_count += _create_student_answers(
                    db, student, all_questions, sr, base_time
                )

            db.commit()
            logger.info("Seed data created successfully!")
            logger.info("  - 1 admin (admin@smartexam.com / 123456)")
            logger.info("  - 2 teachers (dawnilarwin@gmail.com, dawnweniwin@gmail.com / 123456)")
            logger.info("  - 2 students (pyaesoneaung@gmail.com, pyaemyatphyo@gmail.com / 123456)")
            logger.info("  - 2 subjects, 2 exams, 10 questions")
            logger.info(f"  - {answer_count} student answers with scores")

        # ─────────────────────────────────────────────────────────────────────
        # 6. ADD 3 EXTRA STUDENTS (independently idempotent)
        #    San Lin Aung, Swan Yee Htut, Thura Hein — each takes both exams.
        # ─────────────────────────────────────────────────────────────────────
        _seed_extra_students(db)
        _seed_new_exams(db)

    except Exception as e:
        db.rollback()
        logger.error(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


def _seed_extra_students(db):
    """Add 3 extra students + their exam answers, idempotently.

    Works whether the full seed just ran or the DB was pre-seeded, because it
    reads subjects/exams/questions back from the DB rather than relying on
    in-memory objects.
    """
    extra_students = [
        ("San Lin Aung", "sanlinaung@gmail.com", "high"),
        ("Swan Yee Htut", "swanyeehtut@gmail.com", "medium_low"),
        ("Thura Hein", "thurahein@gmail.com", "low"),
    ]
    extra_emails = {email for _, email, _ in extra_students}

    already = db.query(User).filter(User.email.in_(extra_emails)).count()
    if already == len(extra_students):
        logger.info("Extra students already exist. Skipping.")
        return

    # Need questions to answer — they must exist (full seed ran or pre-seeded).
    questions = db.query(Question).order_by(Question.id).all()
    if not questions:
        logger.warning("No questions found — cannot seed extra students' answers. Skipping.")
        return

    logger.info("Adding 3 extra students with exam answers...")
    base_time = datetime.utcnow() - timedelta(days=30)

    created = 0
    for name, email, profile in extra_students:
        exists = db.query(User).filter(User.email == email).first()
        if exists:
            logger.info(f"  - {email} already exists, skipping.")
            continue

        student = User(
            name=name,
            email=email,
            hashed_password=get_password_hash(STUDENT_PASSWORD),
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(student)
        db.flush()

        created += _create_student_answers(
            db, student, questions, SCORE_RANGES[profile], base_time
        )

    db.commit()
    logger.info("Extra students created:")
    logger.info("  - San Lin Aung  (sanlinaung@gmail.com / 123456)")
    logger.info("  - Swan Yee Htut (swanyeehtut@gmail.com / 123456)")
    logger.info("  - Thura Hein    (thurahein@gmail.com / 123456)")
    logger.info(f"  - {created} extra student answers with scores")
