import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
export let errorRate = new Rate('errors');

// Test configuration
export let options = {
  stages: [
    { duration: '2m', target: 10 },   // Ramp up to 10 users
    { duration: '5m', target: 10 },   // Stay at 10 users
    { duration: '2m', target: 20 },   // Ramp up to 20 users
    { duration: '5m', target: 20 },   // Stay at 20 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<1000'], // 95% of requests must complete below 1s
    http_req_failed: ['rate<0.1'],     // Error rate must be below 10%
    errors: ['rate<0.1'],              // Custom error rate below 10%
  },
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';

// Test data
const testUsers = [
  { email: 'admin@jota.news', password: 'demo12345' },
  { email: 'editor.politica@jota.news', password: 'demo12345' },
  { email: 'jornalista1@jota.news', password: 'demo12345' },
];

let authToken = null;

export function setup() {
  // Authenticate to get token for protected endpoints
  let loginResponse = http.post(`${BASE_URL}/api/v1/auth/token/`, {
    email: testUsers[0].email,
    password: testUsers[0].password,
  });
  
  if (loginResponse.status === 200) {
    let token = JSON.parse(loginResponse.body).access;
    console.log('Successfully authenticated for load test');
    return { token: token };
  } else {
    console.log('Failed to authenticate for load test');
    return {};
  }
}

export default function(data) {
  let params = {};
  
  if (data.token) {
    params.headers = {
      'Authorization': `Bearer ${data.token}`,
      'Content-Type': 'application/json',
    };
  }

  // Test 1: Health Check
  let healthResponse = http.get(`${BASE_URL}/health/`);
  let healthCheck = check(healthResponse, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 200ms': (r) => r.timings.duration < 200,
  });
  errorRate.add(!healthCheck);

  sleep(0.5);

  // Test 2: API Root
  let apiResponse = http.get(`${BASE_URL}/api/v1/`);
  let apiCheck = check(apiResponse, {
    'API root status is 200': (r) => r.status === 200,
    'API root response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!apiCheck);

  sleep(0.5);

  // Test 3: News Articles List
  let newsResponse = http.get(`${BASE_URL}/api/v1/news/articles/`, params);
  let newsCheck = check(newsResponse, {
    'news list status is 200': (r) => r.status === 200,
    'news list response time < 1000ms': (r) => r.timings.duration < 1000,
    'news list has data': (r) => {
      try {
        let body = JSON.parse(r.body);
        return body.results && Array.isArray(body.results);
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(!newsCheck);

  sleep(0.5);

  // Test 4: Categories List
  let categoriesResponse = http.get(`${BASE_URL}/api/v1/news/categories/`, params);
  let categoriesCheck = check(categoriesResponse, {
    'categories status is 200': (r) => r.status === 200,
    'categories response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!categoriesCheck);

  sleep(0.5);

  // Test 5: Tags List
  let tagsResponse = http.get(`${BASE_URL}/api/v1/news/tags/`, params);
  let tagsCheck = check(tagsResponse, {
    'tags status is 200': (r) => r.status === 200,
    'tags response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(!tagsCheck);

  sleep(0.5);

  // Test 6: News Filtering (random category)
  let filterResponse = http.get(`${BASE_URL}/api/v1/news/articles/?category=politica`, params);
  let filterCheck = check(filterResponse, {
    'filtered news status is 200': (r) => r.status === 200,
    'filtered news response time < 1000ms': (r) => r.timings.duration < 1000,
  });
  errorRate.add(!filterCheck);

  sleep(0.5);

  // Test 7: Search functionality
  let searchResponse = http.get(`${BASE_URL}/api/v1/news/articles/?search=política`, params);
  let searchCheck = check(searchResponse, {
    'search status is 200': (r) => r.status === 200,
    'search response time < 1500ms': (r) => r.timings.duration < 1500,
  });
  errorRate.add(!searchCheck);

  sleep(1);

  // Test 8: Webhook endpoint (simulate news submission)
  if (Math.random() < 0.1) { // 10% of requests test webhook
    let webhookData = {
      title: `Load Test News ${Math.random().toString(36).substring(7)}`,
      content: 'This is a load test news article content. Testing system performance under load.',
      source: 'Load Test Source',
      category: 'politica',
      urgency: false,
    };
    
    let webhookResponse = http.post(
      `${BASE_URL}/api/v1/webhooks/news/`,
      JSON.stringify(webhookData),
      {
        headers: {
          'Content-Type': 'application/json',
          'X-Webhook-Source': 'load-test',
        },
      }
    );
    
    let webhookCheck = check(webhookResponse, {
      'webhook status is 200 or 201': (r) => r.status === 200 || r.status === 201,
      'webhook response time < 2000ms': (r) => r.timings.duration < 2000,
    });
    errorRate.add(!webhookCheck);
  }

  sleep(1);
}

export function teardown(data) {
  console.log('Load test completed');
}