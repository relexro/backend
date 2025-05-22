#!/usr/bin/env node

/**
 * Automated Firebase Token Refresh Script
 * 
 * This script automatically refreshes Firebase ID tokens and updates ~/.zshenv
 * 
 * Usage:
 *   node scripts/refresh-tokens.js
 * 
 * Requirements:
 *   npm install firebase-admin
 */

const admin = require('firebase-admin');
const fs = require('fs');
const path = require('path');
const os = require('os');

// Firebase configuration
const firebaseConfig = {
    apiKey: "AIzaSyDoAzsda-TOwoqcAt7DAsL1GDsp_2NSi30",
    authDomain: "relexro.firebaseapp.com",
    projectId: "relexro",
    storageBucket: "relexro.appspot.com",
    messagingSenderId: "764589667187",
    appId: "1:49787884280:web:80501323bdb2f5fbcb610d"
};

// User configurations for different test users
const TEST_USERS = {
    RELEX_TEST_JWT: {
        uid: 'test-user-uid', // Replace with actual test user UID
        email: 'test@example.com' // Replace with actual test user email
    },
    RELEX_ORG_ADMIN_TEST_JWT: {
        uid: 'org-admin-uid', // Replace with actual org admin UID
        email: 'admin@example.com' // Replace with actual org admin email
    },
    RELEX_ORG_USER_TEST_JWT: {
        uid: 'org-user-uid', // Replace with actual org user UID
        email: 'user@example.com' // Replace with actual org user email
    }
};

async function initializeFirebase() {
    try {
        // Initialize Firebase Admin SDK
        // You'll need to set up a service account key
        const serviceAccount = require('../firebase-service-account-key.json');
        
        admin.initializeApp({
            credential: admin.credential.cert(serviceAccount),
            projectId: firebaseConfig.projectId
        });
        
        console.log('✅ Firebase Admin initialized successfully');
        return true;
    } catch (error) {
        console.error('❌ Firebase initialization failed:', error.message);
        console.log('💡 Make sure you have firebase-service-account-key.json in the project root');
        return false;
    }
}

async function generateCustomToken(uid) {
    try {
        // Generate a custom token with longer expiration (1 hour by default, but can be refreshed)
        const customToken = await admin.auth().createCustomToken(uid, {
            // Add custom claims if needed
            role: 'test-user',
            generated_at: Date.now()
        });
        
        console.log(`✅ Generated custom token for UID: ${uid}`);
        return customToken;
    } catch (error) {
        console.error(`❌ Failed to generate token for UID ${uid}:`, error.message);
        return null;
    }
}

function updateZshEnv(tokens) {
    const zshenvPath = path.join(os.homedir(), '.zshenv');
    
    try {
        let content = '';
        
        // Read existing content if file exists
        if (fs.existsSync(zshenvPath)) {
            content = fs.readFileSync(zshenvPath, 'utf8');
        }
        
        // Update or add each token
        Object.entries(tokens).forEach(([tokenName, tokenValue]) => {
            const regex = new RegExp(`^export ${tokenName}=.*$`, 'm');
            const newLine = `export ${tokenName}="${tokenValue}"`;
            
            if (regex.test(content)) {
                // Update existing line
                content = content.replace(regex, newLine);
            } else {
                // Add new line
                content += `\n${newLine}`;
            }
        });
        
        // Write back to file
        fs.writeFileSync(zshenvPath, content);
        console.log('✅ Updated ~/.zshenv with new tokens');
        
        return true;
    } catch (error) {
        console.error('❌ Failed to update ~/.zshenv:', error.message);
        return false;
    }
}

async function refreshAllTokens() {
    console.log('🔄 Starting token refresh process...');
    
    // Initialize Firebase
    const initialized = await initializeFirebase();
    if (!initialized) {
        process.exit(1);
    }
    
    const tokens = {};
    
    // Generate tokens for each test user
    for (const [tokenName, userConfig] of Object.entries(TEST_USERS)) {
        console.log(`\n🔑 Generating token for ${tokenName}...`);
        const token = await generateCustomToken(userConfig.uid);
        
        if (token) {
            tokens[tokenName] = token;
        } else {
            console.error(`❌ Failed to generate ${tokenName}`);
        }
    }
    
    // Update environment file
    if (Object.keys(tokens).length > 0) {
        const updated = updateZshEnv(tokens);
        if (updated) {
            console.log('\n✅ Token refresh completed successfully!');
            console.log('💡 Run "source ~/.zshenv" to load the new tokens');
        }
    } else {
        console.error('\n❌ No tokens were generated');
        process.exit(1);
    }
}

// Run the refresh process
if (require.main === module) {
    refreshAllTokens().catch(error => {
        console.error('❌ Token refresh failed:', error);
        process.exit(1);
    });
}

module.exports = { refreshAllTokens, generateCustomToken, updateZshEnv };
