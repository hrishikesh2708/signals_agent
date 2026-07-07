// Mirrors backend Pydantic shapes — extend as server routes land.

export interface HealthResponse {
  status: string;
}

// --- Auth ---

export interface RegisterRequest {
  email: string;
  password: string;
  name?: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: UserResponse;
}

/** Shape returned by GET /api/auth/me (BFF). */
export interface AuthMeResponse {
  user: UserResponse | null;
}

export interface AuthSuccessResponse {
  success: true;
}

// --- Projects ---

export interface ProjectCreate {
  name: string;
  description?: string | null;
}

export interface ProjectResponse {
  id: string;
  user_id: string;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectListResponse {
  items: ProjectResponse[];
  total: number;
}

// --- Sessions ---

export interface SessionCreate {
  project_id: string;
  name?: string | null;
}

export interface SessionResponse {
  session_id: string;
  token: string;
  token_type: string;
  name: string;
}

export interface AgentSessionResponse {
  session_id: string;
  project_id: string;
  user_id: string;
  name: string;
  status: string;
  created_at: string;
  updated_at: string;
}
