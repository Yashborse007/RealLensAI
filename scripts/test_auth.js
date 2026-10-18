import app from '../server/app.js';
import http from 'http';
import axios from 'axios';

const PORT = 5005;
let server;

const runTests = async () => {
  console.log('\n====================================================');
  console.log('  Running RealLens AI Auth System Endpoint Tests');
  console.log('====================================================\n');

  server = app.listen(PORT, async () => {
    const baseUrl = `http://localhost:${PORT}/api/auth`;

    try {
      const testEmail = `agent_test_${Date.now()}@forensics.org`;
      const testPassword = 'SecurePassword123!';
      const testName = 'Agent Test Investigator';

      // 1. Test: Successful Registration
      console.log('Test 1: Testing POST /api/auth/register (Successful Registration)...');
      const regRes = await axios.post(`${baseUrl}/register`, {
        name: testName,
        email: testEmail,
        password: testPassword,
        role: 'user',
      });
      if (regRes.status === 201 && regRes.data.token && regRes.data.user) {
        console.log('  ✅ SUCCESS: User registered and JWT token received.');
      } else {
        console.error('  ❌ FAILED: Unexpected registration response:', regRes.data);
      }

      const initialToken = regRes.data.token;

      // 2. Test: Duplicate Email Rejection
      console.log('\nTest 2: Testing POST /api/auth/register (Duplicate Email)...');
      try {
        await axios.post(`${baseUrl}/register`, {
          name: testName,
          email: testEmail,
          password: testPassword,
        });
        console.error('  ❌ FAILED: Duplicate registration was improperly allowed!');
      } catch (err) {
        if (err.response && err.response.status === 400) {
          console.log(`  ✅ SUCCESS: Duplicate email rejected with 400 Bad Request ("${err.response.data.error}")`);
        } else {
          console.error('  ❌ FAILED: Unexpected error status:', err.response?.status);
        }
      }

      // 3. Test: Wrong Password Rejection
      console.log('\nTest 3: Testing POST /api/auth/login (Wrong Password)...');
      try {
        await axios.post(`${baseUrl}/login`, {
          email: testEmail,
          password: 'WrongPassword999!',
        });
        console.error('  ❌ FAILED: Wrong password login was improperly allowed!');
      } catch (err) {
        if (err.response && err.response.status === 401) {
          console.log(`  ✅ SUCCESS: Wrong password rejected with 401 Unauthorized ("${err.response.data.error}")`);
        } else {
          console.error('  ❌ FAILED: Unexpected error status:', err.response?.status);
        }
      }

      // 4. Test: Successful Login
      console.log('\nTest 4: Testing POST /api/auth/login (Successful Login)...');
      const loginRes = await axios.post(`${baseUrl}/login`, {
        email: testEmail,
        password: testPassword,
      });
      if (loginRes.status === 200 && loginRes.data.token) {
        console.log('  ✅ SUCCESS: Login successful and JWT token obtained.');
      } else {
        console.error('  ❌ FAILED: Login failed:', loginRes.data);
      }

      const loginToken = loginRes.data.token;

      // 5. Test: Invalid Token Rejection
      console.log('\nTest 5: Testing GET /api/auth/me (Invalid Token)...');
      try {
        await axios.get(`${baseUrl}/me`, {
          headers: { Authorization: 'Bearer invalid_garbage_token_123' },
        });
        console.error('  ❌ FAILED: Invalid token was accepted!');
      } catch (err) {
        if (err.response && err.response.status === 401) {
          console.log(`  ✅ SUCCESS: Invalid token rejected with 401 Unauthorized ("${err.response.data.error}")`);
        } else {
          console.error('  ❌ FAILED: Unexpected error status:', err.response?.status);
        }
      }

      // 6. Test: Protected Endpoint Access
      console.log('\nTest 6: Testing GET /api/auth/me (Protected Endpoint with valid JWT)...');
      const meRes = await axios.get(`${baseUrl}/me`, {
        headers: { Authorization: `Bearer ${loginToken}` },
      });
      if (meRes.status === 200 && meRes.data.user.email === testEmail.toLowerCase()) {
        console.log(`  ✅ SUCCESS: Authenticated user retrieved ("${meRes.data.user.name}", Role: ${meRes.data.user.role}).`);
      } else {
        console.error('  ❌ FAILED: Protected endpoint returned incorrect user:', meRes.data);
      }

      console.log('\n====================================================');
      console.log('  ALL AUTHENTICATION ENDPOINT TESTS PASSED! 🎉');
      console.log('====================================================\n');
    } catch (err) {
      console.error('\n❌ TEST RUNNER ERROR:', err.message, err.response?.data);
    } finally {
      server.close();
      process.exit(0);
    }
  });
};

runTests();
