const express = require('express');
const cors = require('cors');
const mysql = require('mysql2/promise');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
require('dotenv').config();

const app = express();
app.use(express.json());
app.use(cors());

const pool = mysql.createPool({
    host: process.env.DB_HOST,
    user: process.env.DB_USER,
    password: process.env.DB_PASSWORD,
    database: process.env.DB_NAME || 'legal_chatbot',
    waitForConnections: true,
    connectionLimit: 10
});

// Authentication middleware
const authenticate = async (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
        return res.status(401).json({ error: 'Authorization token required' });
    }
    
    const token = authHeader.split(' ')[1];
    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        req.user = { id: decoded.id };
        next();
    } catch (error) {
        res.status(401).json({ error: 'Invalid or expired token' });
    }
};

// User Registration
app.post('/api/register', async (req, res) => {
    const { email, password } = req.body;
    
    try {
        // Check if user exists
        const [existing] = await pool.query(
            'SELECT * FROM users WHERE email = ?',
            [email]
        );
        
        if (existing.length > 0) {
            return res.status(400).json({ error: 'Email already exists' });
        }

        // Hash password
        const hashedPassword = await bcrypt.hash(password, 10);
        
        // Create user
        const [result] = await pool.query(
            'INSERT INTO users (email, password) VALUES (?, ?)',
            [email, hashedPassword]
        );
        
        res.status(201).json({
            id: result.insertId,
            email
        });
    } catch (error) {
        console.error('Registration error:', error);
        res.status(500).json({ error: 'Server error during registration' });
    }
});

// User Login
app.post('/api/login', async (req, res) => {
    const { email, password } = req.body;

    try {
        // Find user
        const [users] = await pool.query(
            'SELECT * FROM users WHERE email = ?',
            [email]
        );
        
        if (users.length === 0) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Verify password
        const user = users[0];
        const validPassword = await bcrypt.compare(password, user.password);
        
        if (!validPassword) {
            return res.status(401).json({ error: 'Invalid credentials' });
        }

        // Generate JWT
        const token = jwt.sign(
            { id: user.id },
            process.env.JWT_SECRET,
            { expiresIn: '7d' }
        );

        res.json({
            id: user.id,
            email: user.email,
            token
        });
    } catch (error) {
        console.error('Login error:', error);
        res.status(500).json({ error: 'Server error during login' });
    }
});

// Get chat history
app.get('/api/chats', authenticate, async (req, res) => {
    try {
        const [chats] = await pool.query(
            'SELECT * FROM chats WHERE user_id = ? ORDER BY timestamp DESC',
            [req.user.id]
        );
        res.json(chats);
    } catch (error) {
        console.error('Chat history error:', error);
        res.status(500).json({ error: 'Error fetching chat history' });
    }
});

// Save chat message
app.post('/api/chats', authenticate, async (req, res) => {
    const { message, response } = req.body;
    
    try {
        const [result] = await pool.query(
            'INSERT INTO chats (user_id, message, response) VALUES (?, ?, ?)',
            [req.user.id, message, response]
        );
        
        res.status(201).json({
            id: result.insertId,
            message,
            response
        });
    } catch (error) {
        console.error('Save chat error:', error);
        res.status(500).json({ error: 'Error saving chat message' });
    }
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error(err.stack);
    res.status(500).json({ error: 'Something broke!' });
});

app.listen(3001, () => console.log('Node backend running on port 3001'));