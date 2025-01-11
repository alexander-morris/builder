const request = require('supertest');
const app = require('../src/server');

describe('Server Tests', () => {
  test('GET /api/health returns ok status', async () => {
    const response = await request(app)
      .get('/api/health')
      .expect('Content-Type', /json/)
      .expect(200);
      
    expect(response.body).toEqual({ status: 'ok' });
  });
  
  test('Static file serving is configured', async () => {
    await request(app)
      .get('/')
      .expect('Content-Type', /html/)
      .expect(200);
  });
  
  test('Error handling middleware works', async () => {
    const response = await request(app)
      .get('/nonexistent')
      .expect(404);
  });
}); 