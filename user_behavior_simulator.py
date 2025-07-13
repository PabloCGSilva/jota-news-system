#!/usr/bin/env python3
"""
User Behavior Simulator for JOTA News System (Fixed Version)
Simulates realistic user interactions to generate observability data and demonstrate system capabilities.
"""
import requests
import json
import time
import random
import threading
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class JOTAAPIClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.tokens = {}
        self.api_keys = {}
        
    def register_user(self, username, email, password="demo12345"):  # Fixed: 8+ chars
        """Register a new user"""
        try:
            response = self.session.post(f"{self.base_url}/api/v1/auth/register/", {
                'username': username,
                'email': email,
                'password': password,
                'password_confirm': password,
                'first_name': username.split('_')[0].title(),
                'last_name': 'Demo'
            })
            if response.status_code == 201:
                logger.info(f"✅ User registered: {username}")
                return True
            else:
                logger.warning(f"⚠️ Registration failed for {username}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Registration error for {username}: {str(e)}")
            return False
    
    def login_user(self, username, password="demo12345"):  # Fixed: use email field
        """Login user and get JWT token"""
        try:
            email = f"{username}@demo.jota.news"
            # Fixed: Use correct endpoint and send JSON data
            headers = {'Content-Type': 'application/json'}
            data = {
                'email': email,
                'password': password
            }
            response = self.session.post(f"{self.base_url}/api/v1/auth/token/", 
                                       data=json.dumps(data), headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                self.tokens[username] = data['access']
                logger.info(f"✅ User logged in: {username}")
                return True
            else:
                logger.warning(f"⚠️ Login failed for {username}: {response.text}")
                return False
        except Exception as e:
            logger.error(f"❌ Login error for {username}: {str(e)}")
            return False
    
    def get_headers(self, username):
        """Get authorization headers for user"""
        if username in self.tokens:
            return {'Authorization': f'Bearer {self.tokens[username]}'}
        return {}
    
    def list_news(self, username=None, params=None):
        """List news articles"""
        try:
            headers = self.get_headers(username) if username else {}
            # Fixed: use correct endpoint
            url = f"{self.base_url}/api/v1/news/articles/"
            response = self.session.get(url, headers=headers, params=params or {})
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', data) if isinstance(data, dict) else data
                count = len(results) if isinstance(results, list) else data.get('count', 0)
                logger.info(f"📰 Listed {count} news articles")
                return data
            else:
                logger.warning(f"⚠️ Failed to list news: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error listing news: {str(e)}")
            return None
    
    def get_news_detail(self, news_id, username=None):
        """Get news article details"""
        try:
            headers = self.get_headers(username) if username else {}
            # Fixed: use correct endpoint
            response = self.session.get(f"{self.base_url}/api/v1/news/articles/{news_id}/", headers=headers)
            
            if response.status_code == 200:
                logger.info(f"📖 Read news article: {news_id}")
                return response.json()
            else:
                logger.warning(f"⚠️ Failed to get news {news_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Error getting news {news_id}: {str(e)}")
            return None
    
    def search_news(self, query, username=None):
        """Search news articles"""
        try:
            headers = self.get_headers(username) if username else {}
            params = {'search': query}
            # Fixed: use correct endpoint
            response = self.session.get(f"{self.base_url}/api/v1/news/articles/", headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', data) if isinstance(data, dict) else data
                count = len(results) if isinstance(results, list) else data.get('count', 0)
                logger.info(f"🔍 Search '{query}' returned {count} results")
                return data
            else:
                logger.warning(f"⚠️ Search failed: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"❌ Search error: {str(e)}")
            return None
    
    def get_categories(self):
        """Get news categories"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/news/categories/")
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', data) if isinstance(data, dict) else data
                count = len(results) if isinstance(results, list) else 0
                logger.info(f"📁 Retrieved {count} categories")
                return results
            return []
        except Exception as e:
            logger.error(f"❌ Error getting categories: {str(e)}")
            return []
    
    def create_news(self, username, title, content, category_id):
        """Create a news article (requires authentication)"""
        try:
            headers = self.get_headers(username)
            if not headers:
                logger.warning(f"⚠️ No auth token for {username}")
                return None
                
            data = {
                'title': title,
                'content': content,
                'category': category_id,
                'source': 'Demo Source',
                'author': username,
                'is_published': True,
                'priority': random.choice(['low', 'medium', 'high'])
            }
            
            # Fixed: use correct endpoint and content type
            headers['Content-Type'] = 'application/json'
            response = self.session.post(f"{self.base_url}/api/v1/news/articles/", 
                                       data=json.dumps(data), headers=headers)
            
            if response.status_code == 201:
                logger.info(f"✍️ Created news article: {title}")
                return response.json()
            else:
                logger.warning(f"⚠️ Failed to create news: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"❌ Error creating news: {str(e)}")
            return None
    
    def get_user_profile(self, username):
        """Get user profile"""
        try:
            headers = self.get_headers(username)
            response = self.session.get(f"{self.base_url}/api/v1/auth/profile/", headers=headers)
            
            if response.status_code == 200:
                logger.info(f"👤 Retrieved profile for {username}")
                return response.json()
            return None
        except Exception as e:
            logger.error(f"❌ Error getting profile: {str(e)}")
            return None

class UserBehaviorSimulator:
    def __init__(self):
        self.client = JOTAAPIClient()
        self.users = [
            'reader_1', 'reader_2', 'reader_3', 'editor_1', 'editor_2',
            'journalist_1', 'journalist_2', 'admin_user', 'premium_user', 'basic_user'
        ]
        self.search_terms = [
            'política', 'economia', 'STF', 'congresso', 'eleições',
            'PIB', 'inflação', 'juros', 'Selic', 'orçamento',
            'tecnologia', 'inovação', 'sustentabilidade', 'meio ambiente'
        ]
        self.running = False
        self.available_news_ids = []
        
    def setup_users(self):
        """Setup demo users"""
        logger.info("🔧 Setting up demo users...")
        
        for user in self.users:
            email = f"{user}@demo.jota.news"
            
            # Try to register (will fail if user exists, which is fine)
            self.client.register_user(user, email)
            
            # Login user
            self.client.login_user(user)
        
        # Get available news IDs for detail requests
        self._update_available_news()
        
        logger.info("✅ User setup completed")
    
    def _update_available_news(self):
        """Update list of available news IDs"""
        try:
            news_data = self.client.list_news()
            if news_data:
                if isinstance(news_data, dict) and 'results' in news_data:
                    self.available_news_ids = [article['id'] for article in news_data['results']]
                elif isinstance(news_data, list):
                    self.available_news_ids = [article['id'] for article in news_data]
                logger.info(f"📊 Updated available news IDs: {len(self.available_news_ids)} articles")
        except Exception as e:
            logger.error(f"❌ Error updating news IDs: {str(e)}")
    
    def simulate_reader_behavior(self, username):
        """Simulate a typical reader's behavior"""
        try:
            # List news articles
            news_list = self.client.list_news(username)
            if news_list:
                results = news_list.get('results', news_list) if isinstance(news_list, dict) else news_list
                if isinstance(results, list) and results:
                    # Read random articles
                    for _ in range(random.randint(1, 3)):
                        if results:
                            article = random.choice(results)
                            self.client.get_news_detail(article['id'], username)
                            time.sleep(random.uniform(2, 5))  # Reading time
            
            # Perform some searches
            for _ in range(random.randint(1, 2)):
                search_term = random.choice(self.search_terms)
                self.client.search_news(search_term, username)
                time.sleep(random.uniform(1, 3))
            
            # Get user profile occasionally
            if random.random() < 0.3:
                self.client.get_user_profile(username)
                
        except Exception as e:
            logger.error(f"❌ Error in reader behavior for {username}: {str(e)}")
    
    def simulate_editor_behavior(self, username):
        """Simulate editor/journalist behavior"""
        try:
            # Do reader activities first
            self.simulate_reader_behavior(username)
            
            # Create news articles occasionally
            if random.random() < 0.4:  # 40% chance
                categories = self.client.get_categories()
                if categories and isinstance(categories, list) and categories:
                    category = random.choice(categories)
                    # Fixed: handle both dict and direct ID
                    category_id = category.get('id') if isinstance(category, dict) else category
                    
                    title = f"Breaking: {random.choice(self.search_terms).title()} - {datetime.now().strftime('%H:%M')}"
                    content = f"Esta é uma notícia importante sobre {random.choice(self.search_terms)}. " + \
                             "A situação está sendo acompanhada de perto por nossos correspondentes. " * random.randint(3, 6)
                    
                    self.client.create_news(username, title, content, category_id)
                    
        except Exception as e:
            logger.error(f"❌ Error in editor behavior for {username}: {str(e)}")
    
    def simulate_user_session(self, username):
        """Simulate a complete user session"""
        try:
            user_type = 'editor' if 'editor' in username or 'journalist' in username else 'reader'
            
            logger.info(f"🎭 Starting session for {username} ({user_type})")
            
            if user_type == 'editor':
                self.simulate_editor_behavior(username)
            else:
                self.simulate_reader_behavior(username)
                
            # Random delay between sessions
            time.sleep(random.uniform(5, 15))
            
        except Exception as e:
            logger.error(f"❌ Session error for {username}: {str(e)}")
    
    def run_continuous_simulation(self, duration_minutes=30):
        """Run continuous user behavior simulation"""
        logger.info(f"🚀 Starting continuous simulation for {duration_minutes} minutes...")
        
        self.running = True
        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)
        
        # Setup users first
        self.setup_users()
        
        # Create threads for different user types
        threads = []
        
        def user_loop(username):
            while self.running and time.time() < end_time:
                try:
                    self.simulate_user_session(username)
                    # Random delay between user sessions
                    time.sleep(random.uniform(10, 30))
                except Exception as e:
                    logger.error(f"❌ User loop error for {username}: {str(e)}")
                    time.sleep(5)
        
        # Start user simulation threads
        for user in self.users:
            thread = threading.Thread(target=user_loop, args=(user,))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(random.uniform(1, 3))  # Stagger thread starts
        
        try:
            # Monitor simulation
            while time.time() < end_time and self.running:
                remaining = int((end_time - time.time()) / 60)
                logger.info(f"🕐 Simulation running... {remaining} minutes remaining")
                
                # Update available news periodically
                if random.random() < 0.1:  # 10% chance each minute
                    self._update_available_news()
                
                time.sleep(60)  # Status update every minute
                
        except KeyboardInterrupt:
            logger.info("⚠️ Simulation interrupted by user")
        
        # Stop simulation
        self.running = False
        logger.info("🏁 Simulation completed")
        
        # Wait for threads to finish
        for thread in threads:
            thread.join(timeout=5)
    
    def run_burst_test(self, requests_per_second=10, duration_seconds=60):
        """Run a burst test to generate high load"""
        logger.info(f"💥 Starting burst test: {requests_per_second} req/s for {duration_seconds}s")
        
        self.setup_users()
        
        start_time = time.time()
        end_time = start_time + duration_seconds
        request_count = 0
        
        while time.time() < end_time:
            for _ in range(requests_per_second):
                if time.time() >= end_time:
                    break
                    
                # Pick random user and action
                user = random.choice(self.users)
                action = random.choice(['list', 'search', 'detail'])
                
                if action == 'list':
                    self.client.list_news(user)
                elif action == 'search':
                    term = random.choice(self.search_terms)
                    self.client.search_news(term, user)
                elif action == 'detail' and self.available_news_ids:
                    # Fixed: use actual available news IDs
                    news_id = random.choice(self.available_news_ids)
                    self.client.get_news_detail(news_id, user)
                
                request_count += 1
                
                # Small delay to spread requests across the second
                time.sleep(1.0 / requests_per_second)
            
            remaining = int(end_time - time.time())
            if remaining > 0:
                logger.info(f"💥 Burst test: {request_count} requests sent, {remaining}s remaining")
        
        logger.info(f"✅ Burst test completed: {request_count} total requests")

def main():
    """Main function"""
    print("🎭 JOTA News System - User Behavior Simulator (Fixed)")
    print("=" * 55)
    
    simulator = UserBehaviorSimulator()
    
    try:
        print("\nChoose simulation mode:")
        print("1. Continuous simulation (30 minutes)")
        print("2. Short demo (5 minutes)")
        print("3. Burst test (high load)")
        print("4. Setup users only")
        
        choice = input("\nEnter choice (1-4): ").strip()
        
        if choice == '1':
            simulator.run_continuous_simulation(30)
        elif choice == '2':
            simulator.run_continuous_simulation(5)
        elif choice == '3':
            simulator.run_burst_test(requests_per_second=15, duration_seconds=120)
        elif choice == '4':
            simulator.setup_users()
        else:
            print("Invalid choice. Running short demo...")
            simulator.run_continuous_simulation(5)
            
    except KeyboardInterrupt:
        print("\n⚠️ Simulation interrupted")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()