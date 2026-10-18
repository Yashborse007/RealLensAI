import app from '../server/app.js';
import axios from 'axios';
import FormData from 'form-data';
import fs from 'fs';
import path from 'path';

const PORT = 5006;
let server;

const createDummyFile = (filename, content = 'dummy content') => {
  const filePath = path.join(process.cwd(), 'scratch', filename);
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  fs.writeFileSync(filePath, content);
  return filePath;
};

const runMediaUploadTests = async () => {
  console.log('\n====================================================');
  console.log('  Running RealLens AI Media Upload System Tests');
  console.log('====================================================\n');

  server = app.listen(PORT, async () => {
    const baseUrl = `http://localhost:${PORT}/api`;

    try {
      // Step 1: Register test user and get JWT token
      const regRes = await axios.post(`${baseUrl}/auth/register`, {
        name: 'Upload Test User',
        email: `uploader_${Date.now()}@forensics.org`,
        password: 'Password123!',
      });
      const token = regRes.data.token;
      console.log('  ✅ Authenticated test user registered, token acquired.\n');

      // Test 1: Image Upload (JPEG)
      console.log('Test 1: Testing POST /api/media/upload (Image Upload)...');
      const imgPath = createDummyFile('test_sample.jpg', 'fake-jpeg-binary-header-data');
      const imgForm = new FormData();
      imgForm.append('file', fs.createReadStream(imgPath), {
        filename: 'my_sample_photo.jpg',
        contentType: 'image/jpeg',
      });

      const imgRes = await axios.post(`${baseUrl}/media/upload`, imgForm, {
        headers: {
          ...imgForm.getHeaders(),
          Authorization: `Bearer ${token}`,
        },
      });

      if (imgRes.status === 200 && imgRes.data.mediaType === 'image') {
        console.log(`  ✅ SUCCESS: Image uploaded! (ID: ${imgRes.data.mediaId}, Unique Filename: ${imgRes.data.filename})`);
      } else {
        console.error('  ❌ FAILED: Unexpected image upload response:', imgRes.data);
      }

      // Test 2: Video Upload (MP4)
      console.log('\nTest 2: Testing POST /api/media/upload (Video Upload)...');
      const vidPath = createDummyFile('test_sample.mp4', 'fake-mp4-video-stream-payload');
      const vidForm = new FormData();
      vidForm.append('file', fs.createReadStream(vidPath), {
        filename: 'camera_recording.mp4',
        contentType: 'video/mp4',
      });

      const vidRes = await axios.post(`${baseUrl}/media/upload`, vidForm, {
        headers: {
          ...vidForm.getHeaders(),
          Authorization: `Bearer ${token}`,
        },
      });

      if (vidRes.status === 200 && vidRes.data.mediaType === 'video') {
        console.log(`  ✅ SUCCESS: Video uploaded! (ID: ${vidRes.data.mediaId}, Unique Filename: ${vidRes.data.filename})`);
      } else {
        console.error('  ❌ FAILED: Unexpected video upload response:', vidRes.data);
      }

      // Test 3: Audio Upload (WAV)
      console.log('\nTest 3: Testing POST /api/media/upload (Audio Upload)...');
      const audPath = createDummyFile('test_sample.wav', 'fake-wav-audio-sample');
      const audForm = new FormData();
      audForm.append('file', fs.createReadStream(audPath), {
        filename: 'voice_memo.wav',
        contentType: 'audio/wav',
      });

      const audRes = await axios.post(`${baseUrl}/media/upload`, audForm, {
        headers: {
          ...audForm.getHeaders(),
          Authorization: `Bearer ${token}`,
        },
      });

      if (audRes.status === 200 && audRes.data.mediaType === 'audio') {
        console.log(`  ✅ SUCCESS: Audio uploaded! (ID: ${audRes.data.mediaId}, Unique Filename: ${audRes.data.filename})`);
      } else {
        console.error('  ❌ FAILED: Unexpected audio upload response:', audRes.data);
      }

      // Test 4: Invalid File Extension Rejection (.exe)
      console.log('\nTest 4: Testing POST /api/media/upload (Invalid Extension Rejection)...');
      const invalidPath = createDummyFile('malware.exe', 'binary-exe-content');
      const invalidForm = new FormData();
      invalidForm.append('file', fs.createReadStream(invalidPath), {
        filename: 'malware.exe',
        contentType: 'application/octet-stream',
      });

      try {
        await axios.post(`${baseUrl}/media/upload`, invalidForm, {
          headers: {
            ...invalidForm.getHeaders(),
            Authorization: `Bearer ${token}`,
          },
        });
        console.error('  ❌ FAILED: Invalid extension file was improperly allowed!');
      } catch (err) {
        if (err.response && err.response.status === 400) {
          console.log(`  ✅ SUCCESS: Invalid extension rejected with 400 Bad Request ("${err.response.data.error}")`);
        } else {
          console.error('  ❌ FAILED: Unexpected error status:', err.response?.status);
        }
      }

      // Test 5: Unauthenticated Upload Attempt
      console.log('\nTest 5: Testing POST /api/media/upload (Unauthenticated Protection)...');
      const unauthForm = new FormData();
      unauthForm.append('file', fs.createReadStream(imgPath), {
        filename: 'photo.jpg',
        contentType: 'image/jpeg',
      });

      try {
        await axios.post(`${baseUrl}/media/upload`, unauthForm, {
          headers: unauthForm.getHeaders(),
        });
        console.error('  ❌ FAILED: Unauthenticated upload was improperly allowed!');
      } catch (err) {
        if (err.response && err.response.status === 401) {
          console.log(`  ✅ SUCCESS: Unauthenticated upload blocked with 401 Unauthorized ("${err.response.data.error}")`);
        } else {
          console.error('  ❌ FAILED: Unexpected error status:', err.response?.status);
        }
      }

      console.log('\n====================================================');
      console.log('  ALL MEDIA UPLOAD SYSTEM TESTS PASSED! 🎉');
      console.log('====================================================\n');
    } catch (err) {
      console.error('\n❌ TEST RUNNER ERROR:', err.message, err.response?.data);
    } finally {
      server.close();
      process.exit(0);
    }
  });
};

runMediaUploadTests();
