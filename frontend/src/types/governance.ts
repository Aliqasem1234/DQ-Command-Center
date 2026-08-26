export type GovernanceRole = 'owner' | 'steward' | 'curator' | 'analyst';
export type GovernancePolicyStatus = 'draft' | 'approved' | 'active' | 'deprecated' | 'retired';

export interface GovernanceAssignment {
  id: string;
  domain_id: string | null;
  dataset_id: string | null;
  element_id: string | null;
  role: GovernanceRole;
  user_id: string;
  user_name: string | null;
  department_id: string | null;
  responsibility_description: string | null;
  start_date: string | null;
  end_date: string | null;
  is_active: boolean;
  assigned_date: string;
  scope_name: string | null;
}

export interface GovernanceAssignmentCreate {
  domain_id?: string | null;
  dataset_id?: string | null;
  element_id?: string | null;
  role: GovernanceRole;
  user_id: string;
  responsibility_description?: string;
}

export interface GovernancePolicy {
  id: string;
  name: string;
  description: string | null;
  domain_id: string | null;
  dataset_id: string | null;
  policy_type: string;
  policy_definition: Record<string, unknown> | null;
  status: GovernancePolicyStatus;
  effective_date: string | null;
  expiration_date: string | null;
  created_by_id: string | null;
  created_by_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface GovernancePolicyCreate {
  name: string;
  description?: string;
  domain_id?: string | null;
  dataset_id?: string | null;
  policy_type: string;
  status?: GovernancePolicyStatus;
}
