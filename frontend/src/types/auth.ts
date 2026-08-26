export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  user: UserResponse;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name: string;
  department: string | null;
  department_id: string | null;
  department_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  is_super_admin: boolean;
  created_at: string;
  roles: string[];
}

export interface RefreshTokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface ForgotPasswordRequest {
  email: string;
}

export interface ResetPasswordRequest {
  token: string;
  password: string;
}

export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}

export interface MessageResponse {
  message: string;
  detail?: string | null;
}
