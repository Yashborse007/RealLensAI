/**
 * RealLens AI - In-Memory User Store Fallback
 * Provides fallback persistence when MongoDB service is offline or during automated test runs.
 */

import bcrypt from 'bcryptjs';

const users = [];

export const findUserByEmail = (email) => {
  if (!email) return null;
  return users.find((u) => u.email.toLowerCase() === email.toLowerCase()) || null;
};

export const findUserById = (id) => {
  if (!id) return null;
  return users.find((u) => u.id === id || u._id === id) || null;
};

export const saveUser = async ({ name, email, passwordHash, role }) => {
  const newUser = {
    id: `usr_${Math.random().toString(36).substring(2, 9)}`,
    _id: `usr_${Math.random().toString(36).substring(2, 9)}`,
    name,
    email: email.toLowerCase(),
    passwordHash,
    role: role || 'user',
    createdAt: new Date().toISOString(),
  };
  users.push(newUser);
  return newUser;
};

export const compareInMemoryPassword = async (candidatePassword, passwordHash) => {
  if (typeof candidatePassword !== 'string' || typeof passwordHash !== 'string' || !candidatePassword || !passwordHash) {
    return false;
  }
  return await bcrypt.compare(candidatePassword, passwordHash);
};

export const clearUsersStore = () => {
  users.length = 0;
};
