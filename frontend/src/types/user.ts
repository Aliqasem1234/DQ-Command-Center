export interface User {
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
  updated_at: string;
  roles: string[];
}

export interface UserCreate {
  email: string;
  username: string;
  password: string;
  full_name: string;
  department_id?: string;
}

export interface UserUpdate {
  email?: string;
  username?: string;
  full_name?: string;
  department_id?: string;
  is_active?: boolean;
}

export interface UserListResponse {
  items: User[];
  total: number;
  page: number;
  page_size: number;
}

export interface AssignRolesRequest {
  roles: string[];
}
