"""
Message Classification Module for EarnIn Feedback Processing

This module classifies messages into categories and maps them to appropriate Slack channels
based on the provided classification logic.
"""

import json
import random
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class Level1Category(Enum):
    """Level 1 classification categories"""
    PRODUCT_FEEDBACK = "Product Feedback (Feature/Functionality)"
    CUSTOMER_EXPERIENCE = "Customer Experience (CX) & Support"
    TECHNICAL_ISSUES = "Technical Issues / Bugs"
    TRUST_SECURITY = "Trust, Security, and Transparency"
    ONBOARDING = "Onboarding and Account Setup"
    PAYMENTS = "Payments and Cash Out"
    NOTIFICATIONS = "Notifications and Communication"
    GENERAL_SENTIMENT = "General Sentiment"
    NON_RELEVANT = "Non-relevant or Ambiguous"


class Level2Category(Enum):
    """Level 2 classification categories"""
    CASH_OUT = "Cash Out"
    BALANCE_SHIELD = "Balance Shield"
    EARNIN_CARD = "EarnIn Card / Tip Jar"
    LIGHTNING_SPEED = "Lightning Speed / Transfer Mechanism"
    INSIGHTS_TOOLS = "Insights & Financial Tools"
    BANK_CONNECTIONS = "Bank Connections"
    NOTIFICATIONS_REMINDERS = "Notifications & Reminders"
    APP_UX_PERFORMANCE = "App UX / Performance"
    CUSTOMER_SUPPORT = "Customer Support"
    SECURITY_COMPLIANCE = "Security / Compliance"
    NON_RELEVANT = "Non-relevant or Ambiguous"


@dataclass
class ClassificationResult:
    """Result of message classification"""
    level_1_category: str
    level_2_category: str
    slack_channel: str
    jira_ticket: str
    confidence_score: float = 0.0
    reasoning: str = ""


class MessageClassifier:
    """Main classifier for processing messages and determining categories"""
    
    # Mapping from L2 categories to Slack channels (using channel IDs)
    SLACK_CHANNEL_MAPPING = {
        Level2Category.CASH_OUT: "C09LBDF1MT8",  # help-cashout-experience
        Level2Category.BALANCE_SHIELD: "C09LBDF1MT8",  # help-cashout-experience
        Level2Category.EARNIN_CARD: "C09L73ZDGSF",  # help-earnin-card
        Level2Category.LIGHTNING_SPEED: "C09L740CY0K",  # help-money-movement
        Level2Category.INSIGHTS_TOOLS: "C09L74151R9",  # help-analytics
        Level2Category.BANK_CONNECTIONS: "C09LA2A5HUM",  # help-edx-accountverification
        Level2Category.NOTIFICATIONS_REMINDERS: "C09LDGARC9Y",  # help-marketing
        Level2Category.APP_UX_PERFORMANCE: "C09LA2F4S05",  # help-performance-ux
        Level2Category.CUSTOMER_SUPPORT: "C09M7Q7SC0Y",  # help-cx
        Level2Category.SECURITY_COMPLIANCE: "C09LSD9UG2D",  # help-security
        Level2Category.NON_RELEVANT: ""
    }
    
    # Keywords for different categories
    KEYWORDS = {
        Level1Category.PAYMENTS: [
            "cash out", "cashout", "instant cash", "transfer", "withdraw", "deposit",
            "fee", "fees", "cost", "charge", "money", "payment", "balance", "funds",
            "earning", "earnings", "get the earning", "not able to get", "unable to get",
            "not able to cashout", "unable to cashout", "cashout issue", "cashout problem"
        ],
        Level1Category.PRODUCT_FEEDBACK: [
            "feature", "functionality", "tip jar", "earnin card", "insights", "analytics",
            "financial tools", "app", "interface", "ui", "ux", "design", "navigation",
            "product", "earnin product", "liked", "didnt like", "dont like", "like it"
        ],
        Level1Category.TECHNICAL_ISSUES: [
            "bug", "error", "crash", "freeze", "slow", "loading", "connection", "network",
            "technical", "issue", "problem", "broken", "not working", "glitch"
        ],
        Level1Category.CUSTOMER_EXPERIENCE: [
            "support", "help", "customer service", "assistance", "response", "wait time",
            "experience", "satisfaction", "frustrated", "confused", "unclear", "customer support"
        ],
        Level1Category.TRUST_SECURITY: [
            "security", "privacy", "trust", "safe", "secure", "data", "personal information",
            "fraud", "scam", "suspicious", "verification", "identity", "security features"
        ],
        Level1Category.ONBOARDING: [
            "sign up", "signup", "register", "account", "verification", "setup", "onboarding",
            "bank account", "connect", "link", "verify", "document", "id", "bank connection"
        ],
        Level1Category.NOTIFICATIONS: [
            "notification", "alert", "reminder", "email", "sms", "push", "message",
            "communication", "update", "newsletter"
        ]
    }
    
    # L2 specific keywords
    L2_KEYWORDS = {
        Level2Category.CASH_OUT: [
            "cash out", "cashout", "instant cash", "withdraw", "transfer money",
            "fee", "fees", "cost", "charge", "fast", "slow", "delay",
            "not able to cashout", "unable to cashout", "cashout issue", "cashout problem"
        ],
        Level2Category.EARNIN_CARD: [
            "earnin card", "tip jar", "tips", "card", "debit", "spending", "tip", "jar"
        ],
        Level2Category.LIGHTNING_SPEED: [
            "lightning speed", "instant", "fast transfer", "quick", "speed", "delay"
        ],
        Level2Category.INSIGHTS_TOOLS: [
            "insights", "analytics", "financial tools", "spending", "budget", "tracking"
        ],
        Level2Category.BANK_CONNECTIONS: [
            "bank", "account", "connect", "link", "verification", "plaid", "connection", "connecting"
        ],
        Level2Category.APP_UX_PERFORMANCE: [
            "app", "interface", "ui", "ux", "navigation", "crash", "slow", "performance", "confusing"
        ],
        Level2Category.CUSTOMER_SUPPORT: [
            "support", "help", "customer service", "assistance", "response", "customer support"
        ],
        Level2Category.SECURITY_COMPLIANCE: [
            "security", "privacy", "safe", "secure", "fraud", "verification", "security features"
        ]
    }
    
    def __init__(self):
        """Initialize the classifier"""
        self.confidence_threshold = 0.3
    
    def classify_message(self, message: str) -> ClassificationResult:
        """
        Classify a message into categories and return structured result
        
        Args:
            message: The message content to classify
            
        Returns:
            ClassificationResult with category mappings and JIRA ticket
        """
        # Clean and normalize the message
        cleaned_message = self._clean_message(message)
        
        # Perform classification reasoning
        reasoning = self._analyze_message(cleaned_message)
        
        # Determine L1 category
        l1_category, l1_confidence = self._classify_level1(cleaned_message)
        
        # Determine L2 category
        l2_category, l2_confidence = self._classify_level2(cleaned_message, l1_category)
        
        # Get Slack channel
        slack_channel = self.SLACK_CHANNEL_MAPPING.get(l2_category, "")
        
        # Generate JIRA ticket
        jira_ticket = self._generate_jira_ticket()
        
        # Calculate overall confidence
        overall_confidence = (l1_confidence + l2_confidence) / 2
        
        return ClassificationResult(
            level_1_category=l1_category.value,
            level_2_category=l2_category.value,
            slack_channel=slack_channel,
            jira_ticket=jira_ticket,
            confidence_score=overall_confidence,
            reasoning=reasoning
        )
    
    def _clean_message(self, message: str) -> str:
        """Clean and normalize message text"""
        if not message:
            return ""
        
        # Convert to lowercase
        cleaned = message.lower().strip()
        
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        return cleaned
    
    def _analyze_message(self, message: str) -> str:
        """Analyze message and provide reasoning for classification"""
        reasoning_parts = []
        
        # Check for key indicators
        if any(keyword in message for keyword in ["cash out", "cashout", "instant cash"]):
            reasoning_parts.append("Contains cash out related terms")
        
        if any(keyword in message for keyword in ["bug", "error", "crash", "broken"]):
            reasoning_parts.append("Contains technical issue indicators")
        
        if any(keyword in message for keyword in ["support", "help", "assistance"]):
            reasoning_parts.append("Contains customer support indicators")
        
        if any(keyword in message for keyword in ["security", "privacy", "safe"]):
            reasoning_parts.append("Contains security/trust indicators")
        
        if any(keyword in message for keyword in ["app", "interface", "navigation"]):
            reasoning_parts.append("Contains app UX indicators")
        
        if not reasoning_parts:
            reasoning_parts.append("No specific indicators found - general sentiment")
        
        return "; ".join(reasoning_parts)
    
    def _classify_level1(self, message: str) -> Tuple[Level1Category, float]:
        """Classify message into Level 1 category"""
        if not message:
            return Level1Category.NON_RELEVANT, 0.0
        
        # Score each category based on keyword matches
        category_scores = {}
        
        for category, keywords in self.KEYWORDS.items():
            score = 0
            total_keywords = len(keywords)
            
            for keyword in keywords:
                if keyword.lower() in message.lower():
                    # Weight longer keywords more heavily, and give extra weight to specific terms
                    base_weight = len(keyword.split()) * 0.2 + 0.3
                    # Give extra weight to specific important terms
                    if keyword.lower() in ["cashout", "cash out", "instant cash", "withdraw", "transfer money"]:
                        base_weight *= 2.0
                    elif keyword.lower() in ["issue", "problem", "bug", "error", "broken", "not working"]:
                        base_weight *= 1.5
                    score += base_weight
            
            if total_keywords > 0:
                category_scores[category] = score / total_keywords
        
        # If no matches found or very low scores, check for general sentiment
        if not category_scores or max(category_scores.values()) < 0.02:
            # Check for positive/negative sentiment
            positive_words = ["love", "great", "awesome", "amazing", "perfect", "excellent", "good", "thanks", "thank you"]
            negative_words = ["hate", "terrible", "awful", "horrible", "bad", "worst", "disappointed", "frustrated"]
            
            positive_count = sum(1 for word in positive_words if word in message)
            negative_count = sum(1 for word in negative_words if word in message)
            
            if positive_count > 0 or negative_count > 0:
                return Level1Category.GENERAL_SENTIMENT, 0.5
            else:
                return Level1Category.NON_RELEVANT, 0.1
        
        # Return category with highest score
        best_category = max(category_scores, key=category_scores.get)
        confidence = min(category_scores[best_category], 1.0)
        
        return best_category, confidence
    
    def _classify_level2(self, message: str, l1_category: Level1Category) -> Tuple[Level2Category, float]:
        """Classify message into Level 2 category based on L1 category"""
        if l1_category == Level1Category.NON_RELEVANT:
            return Level2Category.NON_RELEVANT, 0.1
        
        if l1_category == Level1Category.GENERAL_SENTIMENT:
            return Level2Category.NON_RELEVANT, 0.3
        
        # Score L2 categories based on keywords
        category_scores = {}
        
        for category, keywords in self.L2_KEYWORDS.items():
            score = 0
            total_keywords = len(keywords)
            
            for keyword in keywords:
                if keyword.lower() in message.lower():
                    base_weight = len(keyword.split()) * 0.2 + 0.3
                    # Give extra weight to specific important terms
                    if keyword.lower() in ["cashout", "cash out", "instant cash", "withdraw", "transfer money"]:
                        base_weight *= 2.0
                    elif keyword.lower() in ["issue", "problem", "bug", "error", "broken", "not working"]:
                        base_weight *= 1.5
                    score += base_weight
            
            if total_keywords > 0:
                category_scores[category] = score / total_keywords
        
        # If no specific L2 matches, use L1 to determine best L2
        if not category_scores or max(category_scores.values()) < 0.1:
            l2_mapping = {
                Level1Category.PAYMENTS: Level2Category.CASH_OUT,
                Level1Category.PRODUCT_FEEDBACK: Level2Category.APP_UX_PERFORMANCE,
                Level1Category.TECHNICAL_ISSUES: Level2Category.APP_UX_PERFORMANCE,
                Level1Category.CUSTOMER_EXPERIENCE: Level2Category.CUSTOMER_SUPPORT,
                Level1Category.TRUST_SECURITY: Level2Category.SECURITY_COMPLIANCE,
                Level1Category.ONBOARDING: Level2Category.BANK_CONNECTIONS,
                Level1Category.NOTIFICATIONS: Level2Category.NOTIFICATIONS_REMINDERS
            }
            
            default_l2 = l2_mapping.get(l1_category, Level2Category.NON_RELEVANT)
            return default_l2, 0.3
        
        # Return L2 category with highest score
        best_category = max(category_scores, key=category_scores.get)
        confidence = min(category_scores[best_category], 1.0)
        
        return best_category, confidence
    
    def _generate_jira_ticket(self) -> str:
        """Generate a random JIRA ticket ID"""
        ticket_number = random.randint(100000, 999999)
        return f"JIRA-{ticket_number}"
    
    def classify_batch(self, messages: List[str]) -> List[ClassificationResult]:
        """Classify multiple messages in batch"""
        results = []
        for message in messages:
            result = self.classify_message(message)
            results.append(result)
        return results
    
    def get_classification_summary(self, results: List[ClassificationResult]) -> Dict:
        """Get summary statistics for batch classification results"""
        summary = {
            "total_messages": len(results),
            "category_distribution": {},
            "slack_channel_distribution": {},
            "average_confidence": 0.0,
            "low_confidence_count": 0
        }
        
        if not results:
            return summary
        
        # Count categories
        for result in results:
            l1 = result.level_1_category
            l2 = result.level_2_category
            channel = result.slack_channel
            
            summary["category_distribution"][l1] = summary["category_distribution"].get(l1, 0) + 1
            summary["slack_channel_distribution"][channel] = summary["slack_channel_distribution"].get(channel, 0) + 1
            
            if result.confidence_score < self.confidence_threshold:
                summary["low_confidence_count"] += 1
        
        # Calculate average confidence
        total_confidence = sum(result.confidence_score for result in results)
        summary["average_confidence"] = total_confidence / len(results)
        
        return summary


def classify_message_simple(message: str) -> Dict:
    """
    Simple function to classify a single message and return JSON result
    
    Args:
        message: The message content to classify
        
    Returns:
        Dictionary with classification results in the required JSON format
    """
    classifier = MessageClassifier()
    result = classifier.classify_message(message)
    
    return {
        "level_1_category": result.level_1_category,
        "level_2_category": result.level_2_category,
        "slack_channel": result.slack_channel,
        "jira_ticket": result.jira_ticket
    }


if __name__ == "__main__":
    # Test the classifier with example messages
    test_messages = [
        "My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!",
        "The app's navigation is confusing and sometimes it crashes when searching for my tip jar earnings.",
        "I just love how easy it is to see my earnings now, thanks!",
        "There's a bug in the app that prevents me from connecting my bank account.",
        "The security features make me feel safe using this app.",
        "I need help with setting up my account verification."
    ]
    
    classifier = MessageClassifier()
    
    print("Testing Message Classifier:")
    print("=" * 50)
    
    for i, message in enumerate(test_messages, 1):
        print(f"\nTest {i}: {message}")
        result = classifier.classify_message(message)
        print(f"L1: {result.level_1_category}")
        print(f"L2: {result.level_2_category}")
        print(f"Slack: {result.slack_channel}")
        print(f"JIRA: {result.jira_ticket}")
        print(f"Confidence: {result.confidence_score:.2f}")
        print(f"Reasoning: {result.reasoning}")
        print("-" * 30)
