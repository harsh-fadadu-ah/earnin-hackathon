"""
Enhanced Message Classifier for EarnIn Feedback

This module implements the classification system that:
1. Classifies messages into Level 1 and Level 2 categories
2. Maps to appropriate Slack channels
3. Generates JIRA tickets
4. Handles both positive and negative sentiment
"""

import json
import random
import logging
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ClassificationResult:
    """Result of message classification"""
    level_1_category: str
    level_2_category: str
    slack_channel: str
    jira_ticket: str
    sentiment: str  # "positive", "negative", "neutral"
    confidence: float
    reasoning: str


class EnhancedMessageClassifier:
    """Enhanced classifier that implements the EarnIn feedback classification system"""
    
    def __init__(self):
        # Level 1 categories
        self.level_1_categories = [
            "Product Feedback (Feature/Functionality)",
            "Customer Experience (CX) & Support", 
            "Technical Issues / Bugs",
            "Trust, Security, and Transparency",
            "Onboarding and Account Setup",
            "Payments and Cash Out",
            "Notifications and Communication",
            "General Sentiment",
            "Non-relevant or Ambiguous"
        ]
        
        # Level 2 to Slack channel mapping
        self.l2_to_slack_mapping = {
            "Cash Out": "#help-cashout-experience",
            "Balance Shield": "",  # No specific channel
            "EarnIn Card / Tip Jar": "#help-earnin-card",
            "Lightning Speed / Transfer Mechanism": "#help-money-movement",
            "Insights & Financial Tools": "#help-analytics",
            "Bank Connections": "#help-edx-accountverification",
            "Notifications & Reminders": "#help-marketing",
            "App UX / Performance": "#help-performance-ux",
            "Customer Support": "#help-cx",
            "Security / Compliance": "#help-security",
            "Non-relevant or Ambiguous": ""
        }
        
        # Keywords for classification
        self.classification_keywords = {
            "Payments and Cash Out": [
                "cash out", "cashout", "withdraw", "transfer", "money", "payment", 
                "fee", "cost", "charge", "instant", "lightning speed", "balance"
            ],
            "Technical Issues / Bugs": [
                "crash", "error", "bug", "broken", "not working", "freeze", 
                "glitch", "malfunction", "technical", "issue", "problem"
            ],
            "Trust, Security, and Transparency": [
                "security", "password", "exposed", "privacy", "trust", "safe", 
                "secure", "hack", "breach", "data", "personal information"
            ],
            "App UX / Performance": [
                "ui", "ux", "interface", "navigation", "slow", "performance", 
                "design", "layout", "confusing", "difficult", "user experience"
            ],
            "Customer Experience (CX) & Support": [
                "support", "help", "customer service", "service", "assistance", 
                "response", "contact", "reach out", "escalate"
            ],
            "EarnIn Card / Tip Jar": [
                "card", "tip jar", "tips", "earnings", "income", "daily", 
                "weekly", "earning", "tips jar"
            ],
            "Bank Connections": [
                "bank", "account", "connection", "linked", "verification", 
                "connect", "disconnect", "banking"
            ],
            "Notifications and Communication": [
                "notification", "alert", "reminder", "email", "sms", "message", 
                "communication", "update", "news"
            ],
            "Onboarding and Account Setup": [
                "sign up", "signup", "register", "account", "setup", "onboarding", 
                "verification", "kyc", "identity"
            ]
        }
        
        # Sentiment keywords
        self.positive_keywords = [
            "love", "great", "awesome", "amazing", "perfect", "excellent", "good", 
            "thanks", "thank you", "wonderful", "fantastic", "brilliant", "outstanding",
            "helpful", "useful", "satisfied", "happy", "pleased", "impressed",
            "recommend", "best", "top", "exceeded", "surpassed", "delighted"
        ]
        
        self.negative_keywords = [
            "hate", "terrible", "awful", "horrible", "bad", "worst", "disappointed", 
            "frustrated", "angry", "annoyed", "upset", "disgusted", "displeased",
            "broken", "bug", "error", "issue", "problem", "complaint", "concern",
            "unhappy", "unsatisfied", "poor", "fail", "failed", "failure",
            "slow", "crashed", "freeze", "glitch", "malfunction", "defective"
        ]
        
        # Problem-indicating phrases (should be treated as negative)
        self.problem_phrases = [
            "not working", "not getting", "not able to", "cannot", "can't", "unable to",
            "not receiving", "not processing", "not loading", "not responding",
            "not functioning", "not accessible", "not available", "not connecting",
            "not syncing", "not updating", "not downloading", "not uploading",
            "not sending", "not receiving", "not displaying", "not showing"
        ]
    
    def analyze_sentiment(self, message: str) -> Tuple[str, float, str]:
        """
        Analyze sentiment of a message
        
        Args:
            message: The message content to analyze
            
        Returns:
            Tuple of (sentiment, confidence, reasoning)
        """
        if not message:
            return "neutral", 0.0, "Empty message"
        
        message_lower = message.lower()
        
        # Check for problem-indicating phrases first (these should be negative)
        problem_phrases_found = [phrase for phrase in self.problem_phrases if phrase in message_lower]
        if problem_phrases_found:
            return "negative", 0.8, f"Problem phrases detected: {problem_phrases_found}"
        
        # Count positive and negative keywords
        positive_count = sum(1 for word in self.positive_keywords if word in message_lower)
        negative_count = sum(1 for word in self.negative_keywords if word in message_lower)
        
        # Calculate confidence based on keyword matches
        total_keywords = positive_count + negative_count
        if total_keywords == 0:
            return "neutral", 0.3, "No clear sentiment indicators"
        
        # Determine sentiment based on keyword counts
        if positive_count > negative_count:
            confidence = min(positive_count / (positive_count + negative_count), 1.0)
            reasoning = f"Positive keywords: {positive_count}, Negative keywords: {negative_count}"
            return "positive", confidence, reasoning
        elif negative_count > positive_count:
            confidence = min(negative_count / (positive_count + negative_count), 1.0)
            reasoning = f"Negative keywords: {negative_count}, Positive keywords: {positive_count}"
            return "negative", confidence, reasoning
        else:
            return "neutral", 0.4, f"Mixed sentiment: {positive_count} positive, {negative_count} negative keywords"
    
    def classify_message(self, message: str) -> ClassificationResult:
        """
        Classify a message according to the EarnIn feedback system
        
        Args:
            message: The message content to classify
            
        Returns:
            ClassificationResult with all classification details
        """
        if not message:
            return self._create_result(
                "Non-relevant or Ambiguous", "Non-relevant or Ambiguous", 
                "", "neutral", 0.0, "Empty message"
            )
        
        message_lower = message.lower()
        
        # Step 1: Analyze sentiment
        sentiment, sentiment_confidence, sentiment_reasoning = self.analyze_sentiment(message)
        
        # Step 2: Classify into Level 1 category
        level_1_category = self._classify_level_1(message_lower)
        
        # Step 3: Determine Level 2 category
        level_2_category = self._classify_level_2(message_lower, level_1_category)
        
        # Step 4: Map to Slack channel
        slack_channel = self.l2_to_slack_mapping.get(level_2_category, "")
        
        # Step 5: Generate JIRA ticket
        jira_ticket = self._generate_jira_ticket()
        
        # Step 6: Create reasoning
        reasoning = f"L1: {level_1_category} (based on keywords), L2: {level_2_category}, Sentiment: {sentiment} ({sentiment_reasoning})"
        
        return ClassificationResult(
            level_1_category=level_1_category,
            level_2_category=level_2_category,
            slack_channel=slack_channel,
            jira_ticket=jira_ticket,
            sentiment=sentiment,
            confidence=sentiment_confidence,
            reasoning=reasoning
        )
    
    def _classify_level_1(self, message_lower: str) -> str:
        """Classify message into Level 1 category"""
        category_scores = {}
        
        # Priority order for more specific categories first
        priority_categories = [
            "Trust, Security, and Transparency",
            "Payments and Cash Out", 
            "Technical Issues / Bugs",
            "Customer Experience (CX) & Support",
            "EarnIn Card / Tip Jar",
            "Bank Connections",
            "Notifications and Communication",
            "Onboarding and Account Setup"
        ]
        
        # Check priority categories first
        for category in priority_categories:
            if category in self.classification_keywords:
                keywords = self.classification_keywords[category]
                score = sum(1 for keyword in keywords if keyword in message_lower)
                if score > 0:
                    category_scores[category] = score
        
        # Check remaining categories
        for category, keywords in self.classification_keywords.items():
            if category not in priority_categories:
                score = sum(1 for keyword in keywords if keyword in message_lower)
                if score > 0:
                    category_scores[category] = score
        
        if category_scores:
            # Return category with highest score
            return max(category_scores, key=category_scores.get)
        
        # Check for general sentiment indicators
        if any(word in message_lower for word in self.positive_keywords + self.negative_keywords):
            return "General Sentiment"
        
        return "Non-relevant or Ambiguous"
    
    def _classify_level_2(self, message_lower: str, level_1_category: str) -> str:
        """Classify message into Level 2 category based on Level 1"""
        
        if level_1_category == "Payments and Cash Out":
            if any(word in message_lower for word in ["cash out", "cashout", "withdraw", "instant", "lightning"]):
                return "Cash Out"
            elif any(word in message_lower for word in ["transfer", "money movement", "send"]):
                return "Lightning Speed / Transfer Mechanism"
            elif any(word in message_lower for word in ["balance", "shield"]):
                return "Balance Shield"
        
        elif level_1_category == "Technical Issues / Bugs":
            if any(word in message_lower for word in ["ui", "ux", "interface", "navigation", "design", "slow", "performance"]):
                return "App UX / Performance"
            else:
                return "App UX / Performance"  # Default for technical issues (crashes, bugs, etc.)
        
        elif level_1_category == "Trust, Security, and Transparency":
            return "Security / Compliance"
        
        elif level_1_category == "Customer Experience (CX) & Support":
            return "Customer Support"
        
        elif level_1_category == "EarnIn Card / Tip Jar":
            if any(word in message_lower for word in ["card", "tip jar", "tips"]):
                return "EarnIn Card / Tip Jar"
            elif any(word in message_lower for word in ["earning", "income", "daily"]):
                return "Insights & Financial Tools"
        
        elif level_1_category == "Bank Connections":
            return "Bank Connections"
        
        elif level_1_category == "Notifications and Communication":
            return "Notifications & Reminders"
        
        elif level_1_category == "Onboarding and Account Setup":
            return "Bank Connections"  # Often involves verification
        
        elif level_1_category == "General Sentiment":
            return "Non-relevant or Ambiguous"
        
        return "Non-relevant or Ambiguous"
    
    def _generate_jira_ticket(self) -> str:
        """Generate a random JIRA ticket ID"""
        ticket_number = random.randint(100000, 999999)
        return f"JIRA-{ticket_number}"
    
    def _create_result(self, level_1: str, level_2: str, slack_channel: str, 
                      sentiment: str, confidence: float, reasoning: str) -> ClassificationResult:
        """Create a ClassificationResult object"""
        return ClassificationResult(
            level_1_category=level_1,
            level_2_category=level_2,
            slack_channel=slack_channel,
            jira_ticket=self._generate_jira_ticket(),
            sentiment=sentiment,
            confidence=confidence,
            reasoning=reasoning
        )
    
    def classify_and_format_json(self, message: str) -> str:
        """
        Classify message and return formatted JSON string
        
        Args:
            message: The message content to classify
            
        Returns:
            JSON string in the required format
        """
        result = self.classify_message(message)
        
        return json.dumps({
            "level_1_category": result.level_1_category,
            "level_2_category": result.level_2_category,
            "slack_channel": result.slack_channel,
            "jira_ticket": result.jira_ticket
        }, indent=2)


# Convenience functions
def classify_message(message: str) -> ClassificationResult:
    """Classify a single message"""
    classifier = EnhancedMessageClassifier()
    return classifier.classify_message(message)


def classify_message_json(message: str) -> str:
    """Classify a message and return JSON string"""
    classifier = EnhancedMessageClassifier()
    return classifier.classify_and_format_json(message)


if __name__ == "__main__":
    # Test the classifier
    test_messages = [
        "My instant cash out took much longer than usual, and I couldn't figure out what the fee was for. Help!",
        "The app's navigation is confusing and sometimes it crashes when searching for my tip jar earnings.",
        "I just love how easy it is to see my earnings now, thanks!",
        "there is earnin security issue in app. password is exposed to public.",
        "I am facing issue in earnin app. i am not able to cashout using this. Cashout issue!",
        "Bad ui, didn't like it",
        "Good earnin product, liked cashout feature"
    ]
    
    classifier = EnhancedMessageClassifier()
    
    for message in test_messages:
        print(f"\nMessage: {message}")
        result = classifier.classify_message(message)
        print(f"Classification: {result.level_1_category} -> {result.level_2_category}")
        print(f"Slack Channel: {result.slack_channel}")
        print(f"JIRA Ticket: {result.jira_ticket}")
        print(f"Sentiment: {result.sentiment} (confidence: {result.confidence:.2f})")
        print(f"JSON: {classifier.classify_and_format_json(message)}")
