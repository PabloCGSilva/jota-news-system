"""
News classification engine with NLP capabilities.
"""
import re
import logging
import pickle
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime

# NLP libraries
try:
    import nltk
    from nltk.corpus import stopwords
    from nltk.tokenize import word_tokenize
    from nltk.stem import PorterStemmer
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.linear_model import LogisticRegression
    from sklearn.svm import SVC
    from sklearn.ensemble import VotingClassifier
    from sklearn.metrics import accuracy_score, classification_report
    from sklearn.model_selection import train_test_split
    NLTK_AVAILABLE = True
except ImportError:
    NLTK_AVAILABLE = False

from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)


class NewsClassifier:
    """
    Main news classification engine.
    """
    
    def __init__(self):
        self.stemmer = PorterStemmer() if NLTK_AVAILABLE else None
        
        # Try to load NLTK stopwords, fallback to empty set if not available
        try:
            self.stop_words = set(stopwords.words('portuguese')) if NLTK_AVAILABLE else set()
        except LookupError:
            logger.warning("NLTK stopwords not available, using default Portuguese stopwords")
            self.stop_words = set()
        self.vectorizer = None
        self.model = None
        self.categories = {}
        self.subcategories = {}
        self._load_categories()
        
        # Add Brazilian Portuguese stop words
        self.stop_words.update([
            'de', 'da', 'do', 'das', 'dos', 'em', 'na', 'no', 'nas', 'nos',
            'para', 'por', 'com', 'sem', 'sob', 'sobre', 'entre', 'contra',
            'durante', 'após', 'antes', 'através', 'até', 'desde', 'é', 'foi',
            'ser', 'estar', 'ter', 'haver', 'que', 'qual', 'quando', 'onde',
            'como', 'porque', 'porquê', 'muito', 'mais', 'menos', 'também',
            'ainda', 'já', 'sempre', 'nunca', 'hoje', 'ontem', 'amanhã'
        ])
    
    def _load_categories(self):
        """Load categories and subcategories from database."""
        try:
            from django.db import connection
            from apps.news.models import Category, Subcategory
            
            # Check if tables exist before querying
            table_names = connection.introspection.table_names()
            if 'news_category' not in table_names:
                logger.warning("Category tables don't exist yet, will load later")
                return
            
            # Load categories
            for category in Category.objects.filter(is_active=True):
                self.categories[category.name.lower()] = {
                    'id': category.id,
                    'name': category.name,
                    'keywords': [kw.lower() for kw in category.keywords],
                    'subcategories': {}
                }
            
            # Load subcategories
            for subcategory in Subcategory.objects.filter(is_active=True):
                cat_name = subcategory.category.name.lower()
                if cat_name in self.categories:
                    self.categories[cat_name]['subcategories'][subcategory.name.lower()] = {
                        'id': subcategory.id,
                        'name': subcategory.name,
                        'keywords': [kw.lower() for kw in subcategory.keywords]
                    }
                    
        except Exception as e:
            logger.warning(f"Categories not loaded yet: {e}")
    
    def preprocess_text(self, text: str) -> str:
        """
        Preprocess text for classification.
        """
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and numbers
        text = re.sub(r'[^a-záàâãéèêíìîóòôõúùûç\s]', ' ', text)
        
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Tokenize and remove stop words
        if NLTK_AVAILABLE:
            tokens = word_tokenize(text, language='portuguese')
            tokens = [self.stemmer.stem(token) for token in tokens 
                     if token not in self.stop_words and len(token) > 2]
            return ' '.join(tokens)
        else:
            # Simple fallback without NLTK
            words = text.split()
            words = [word for word in words 
                    if word not in self.stop_words and len(word) > 2]
            return ' '.join(words)
    
    def extract_features(self, text: str) -> Dict[str, float]:
        """
        Extract features from text for classification.
        """
        features = {}
        
        # Text length features
        features['text_length'] = len(text)
        features['word_count'] = len(text.split())
        features['avg_word_length'] = sum(len(word) for word in text.split()) / max(len(text.split()), 1)
        
        # Keyword presence features
        text_lower = text.lower()
        
        # Category-specific keywords
        for category, config in self.categories.items():
            keyword_count = sum(1 for keyword in config['keywords'] if keyword in text_lower)
            features[f'category_{category}_keywords'] = keyword_count
        
        # Urgency indicators
        urgency_keywords = ['urgente', 'breaking', 'última hora', 'agora', 'emergência']
        features['urgency_score'] = sum(1 for keyword in urgency_keywords if keyword in text_lower)
        
        # Time-related features
        time_keywords = ['hoje', 'ontem', 'amanhã', 'semana', 'mês', 'ano']
        features['time_relevance'] = sum(1 for keyword in time_keywords if keyword in text_lower)
        
        return features
    
    def classify_by_keywords(self, title: str, content: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Classify news using keyword matching.
        """
        text = f"{title} {content}".lower()
        
        # Score each category
        category_scores = {}
        
        for category, config in self.categories.items():
            score = 0
            
            # Check category keywords
            for keyword in config['keywords']:
                if keyword in text:
                    score += 1
            
            # Bonus for title matches
            for keyword in config['keywords']:
                if keyword in title.lower():
                    score += 0.5
            
            if score > 0:
                category_scores[category] = score
        
        if not category_scores:
            return None, None, 0.0
        
        # Find best category
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        
        # Normalize confidence
        total_keywords = sum(len(config['keywords']) for config in self.categories.values())
        confidence = min(best_score / max(total_keywords / len(self.categories), 1), 1.0)
        
        # Try to find subcategory
        best_subcategory = None
        subcategory_scores = {}
        
        if best_category in self.categories:
            for subcat, subconfig in self.categories[best_category]['subcategories'].items():
                subscore = 0
                for keyword in subconfig['keywords']:
                    if keyword in text:
                        subscore += 1
                
                if subscore > 0:
                    subcategory_scores[subcat] = subscore
        
        if subcategory_scores:
            best_subcategory = max(subcategory_scores, key=subcategory_scores.get)
        
        return best_category, best_subcategory, confidence
    
    def classify_by_ml(self, title: str, content: str) -> Tuple[Optional[str], Optional[str], float]:
        """
        Classify news using machine learning.
        """
        if not self.model or not self.vectorizer:
            return None, None, 0.0
        
        try:
            # Preprocess text
            text = self.preprocess_text(f"{title} {content}")
            
            # Vectorize
            text_vector = self.vectorizer.transform([text])
            
            # Predict
            prediction = self.model.predict(text_vector)[0]
            probabilities = self.model.predict_proba(text_vector)[0]
            
            # Get confidence
            confidence = max(probabilities)
            
            return prediction, None, confidence
            
        except Exception as e:
            logger.error(f"Error in ML classification: {e}")
            return None, None, 0.0
    
    def classify_urgency(self, title: str, content: str) -> Tuple[bool, float]:
        """
        Determine if news is urgent.
        """
        text = f"{title} {content}".lower()
        
        # Urgent keywords and their weights
        urgent_indicators = {
            'urgente': 1.0,
            'breaking': 1.0,
            'última hora': 1.0,
            'agora': 0.8,
            'emergência': 0.9,
            'alerta': 0.7,
            'atenção': 0.6,
            'importante': 0.5,
            'crítico': 0.8,
            'grave': 0.7,
        }
        
        urgency_score = 0
        for keyword, weight in urgent_indicators.items():
            if keyword in text:
                urgency_score += weight
        
        # Check for time-sensitive patterns
        time_patterns = [
            r'\d+\s*hora',  # X horas
            r'\d+\s*minuto',  # X minutos
            r'neste\s+momento',  # neste momento
            r'agora\s+mesmo',  # agora mesmo
            r'acaba\s+de',  # acaba de
        ]
        
        for pattern in time_patterns:
            if re.search(pattern, text):
                urgency_score += 0.5
        
        # Normalize score
        urgency_score = min(urgency_score, 1.0)
        
        # Determine if urgent
        is_urgent = urgency_score >= 0.6
        
        return is_urgent, urgency_score
    
    def classify_news(self, title: str, content: str, method: str = 'hybrid') -> Dict:
        """
        Main classification function.
        """
        start_time = timezone.now()
        
        result = {
            'category': None,
            'subcategory': None,
            'category_confidence': 0.0,
            'subcategory_confidence': 0.0,
            'is_urgent': False,
            'urgency_confidence': 0.0,
            'method': method,
            'processing_time': 0.0,
            'details': {}
        }
        
        try:
            # Keyword-based classification
            keyword_category, keyword_subcategory, keyword_confidence = self.classify_by_keywords(title, content)
            
            # ML-based classification
            ml_category, ml_subcategory, ml_confidence = self.classify_by_ml(title, content)
            
            # Urgency classification
            is_urgent, urgency_confidence = self.classify_urgency(title, content)
            
            # Choose best classification based on method
            if method == 'keyword':
                result['category'] = keyword_category
                result['subcategory'] = keyword_subcategory
                result['category_confidence'] = keyword_confidence
                result['subcategory_confidence'] = keyword_confidence * 0.8 if keyword_subcategory else 0.0
                
            elif method == 'ml':
                result['category'] = ml_category
                result['subcategory'] = ml_subcategory
                result['category_confidence'] = ml_confidence
                result['subcategory_confidence'] = ml_confidence * 0.8 if ml_subcategory else 0.0
                
            elif method == 'hybrid':
                # Combine keyword and ML results
                if keyword_confidence > ml_confidence:
                    result['category'] = keyword_category
                    result['subcategory'] = keyword_subcategory
                    result['category_confidence'] = keyword_confidence
                    result['subcategory_confidence'] = keyword_confidence * 0.8 if keyword_subcategory else 0.0
                else:
                    result['category'] = ml_category
                    result['subcategory'] = ml_subcategory
                    result['category_confidence'] = ml_confidence
                    result['subcategory_confidence'] = ml_confidence * 0.8 if ml_subcategory else 0.0
                
                # Boost confidence if both methods agree
                if keyword_category == ml_category and keyword_category:
                    result['category_confidence'] = min(result['category_confidence'] * 1.2, 1.0)
            
            # Set urgency
            result['is_urgent'] = is_urgent
            result['urgency_confidence'] = urgency_confidence
            
            # Calculate processing time
            processing_time = (timezone.now() - start_time).total_seconds()
            result['processing_time'] = processing_time
            
            # Add details
            result['details'] = {
                'keyword_result': {
                    'category': keyword_category,
                    'subcategory': keyword_subcategory,
                    'confidence': keyword_confidence
                },
                'ml_result': {
                    'category': ml_category,
                    'subcategory': ml_subcategory,
                    'confidence': ml_confidence
                },
                'urgency_result': {
                    'is_urgent': is_urgent,
                    'confidence': urgency_confidence
                },
                'features': self.extract_features(f"{title} {content}")
            }
            
        except Exception as e:
            logger.error(f"Error in news classification: {e}")
            result['error'] = str(e)
        
        return result
    
    def train_model(self, training_data: List[Tuple[str, str]], labels: List[str]) -> Dict:
        """
        Train machine learning model.
        """
        if not NLTK_AVAILABLE:
            return {'error': 'NLTK not available for ML training'}
        
        try:
            # Preprocess training data
            processed_texts = []
            for title, content in training_data:
                processed_text = self.preprocess_text(f"{title} {content}")
                processed_texts.append(processed_text)
            
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                processed_texts, labels, test_size=0.2, random_state=42
            )
            
            # Create TF-IDF vectorizer
            self.vectorizer = TfidfVectorizer(
                max_features=5000,
                min_df=2,
                max_df=0.8,
                ngram_range=(1, 2)
            )
            
            # Fit vectorizer and transform data
            X_train_tfidf = self.vectorizer.fit_transform(X_train)
            X_test_tfidf = self.vectorizer.transform(X_test)
            
            # Create ensemble model
            nb_model = MultinomialNB()
            lr_model = LogisticRegression(random_state=42)
            svm_model = SVC(probability=True, random_state=42)
            
            self.model = VotingClassifier(
                estimators=[
                    ('nb', nb_model),
                    ('lr', lr_model),
                    ('svm', svm_model)
                ],
                voting='soft'
            )
            
            # Train model
            self.model.fit(X_train_tfidf, y_train)
            
            # Evaluate model
            y_pred = self.model.predict(X_test_tfidf)
            accuracy = accuracy_score(y_test, y_pred)
            
            # Get classification report
            report = classification_report(y_test, y_pred, output_dict=True)
            
            return {
                'accuracy': accuracy,
                'report': report,
                'training_samples': len(X_train),
                'test_samples': len(X_test),
                'features': self.vectorizer.get_feature_names_out()[:100].tolist()
            }
            
        except Exception as e:
            logger.error(f"Error training model: {e}")
            return {'error': str(e)}
    
    def save_model(self, filepath: str) -> bool:
        """
        Save trained model to file.
        """
        try:
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            model_data = {
                'model': self.model,
                'vectorizer': self.vectorizer,
                'categories': self.categories,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(filepath, 'wb') as f:
                pickle.dump(model_data, f)
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {e}")
            return False
    
    def load_model(self, filepath: str) -> bool:
        """
        Load trained model from file.
        """
        try:
            with open(filepath, 'rb') as f:
                model_data = pickle.load(f)
            
            self.model = model_data['model']
            self.vectorizer = model_data['vectorizer']
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {e}")
            return False


# Global classifier instance
classifier = NewsClassifier()