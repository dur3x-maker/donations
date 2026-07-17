export type Owner = {
  id: string;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
};

export type CampaignListItem = {
  id: string;
  owner_id: string;
  title: string;
  description: string;
  description_preview: string;
  target_amount: string;
  current_amount: string;
  category: CampaignCategory;
  cover_image_url?: string | null;
  is_verified: boolean;
  is_active: boolean;
  status: "ACTIVE" | "PENDING_REVIEW" | "REVISION_REQUIRED" | "REJECTED" | "GOAL_REACHED" | "AWAITING_REPORT" | "COMPLETED";
  has_completion_report: boolean;
  report_requested_at?: string | null;
  report_completed_at?: string | null;
  report_overdue: boolean;
  created_at: string;
  progress_percentage: number;
  owner?: Owner | null;
  contributors_count: number;
};

export type PublicContribution = {
  id: string;
  amount: string;
  donor_name?: string | null;
  created_at: string;
};

export type CampaignDetail = CampaignListItem & {
  description: string;
};

export type CompletedCampaignListItem = CampaignListItem & {
  completion_report_preview?: string | null;
  completion_photos: Array<{
    id: string;
    image_url: string;
    created_at: string;
  }>;
};

export type CampaignUpdateItem = {
  id: string;
  campaign_id: string;
  author_id: string;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
  photos: Array<{
    id: string;
    image_url: string;
    created_at: string;
  }>;
};

export type AuthorReputation = {
  campaigns_created: number;
  campaigns_completed: number;
  campaigns_with_reports: number;
  campaigns_without_reports: number;
  total_raised_amount: string;
};

export type ContributionProgress = {
  confirmed_contributions_count: number;
  required_contributions_count: number;
  can_create_campaign: boolean;
  has_unfinished_campaign: boolean;
  can_open_bank_account: boolean;
  has_bank_account: boolean;
  bank_account_application_status?: BankAccountApplicationStatus | null;
};

export type BankAccountApplicationStatus = "PENDING" | "APPROVED" | "REJECTED";

export type BankAccountApplication = {
  id: string;
  user_id: string;
  status: BankAccountApplicationStatus;
  created_at: string;
  updated_at: string;
};

export type BankAccountApplicationState = {
  can_open_bank_account: boolean;
  has_bank_account: boolean;
  application_status?: BankAccountApplicationStatus | null;
  application?: BankAccountApplication | null;
};

export type ProfileSummary = ContributionProgress & {
  supported_campaigns_count: number;
  total_donated_amount: string;
  last_contribution_at?: string | null;
  supported_campaigns_current_amount: string;
  contributions_last_30_days: number;
  supported_campaigns_last_30_days: number;
  achievements: Array<{
    id: string;
    title: string;
    copy: string;
    achieved_at: string;
  }>;
  achievements_last_30_days: number;
  user_level: string;
  community_top_percent?: number | null;
  community_rank?: number | null;
  active_contributors_count: number;
  recent_contributions: Array<{
    id: string;
    campaign_id: string;
    campaign_title: string;
    amount: string;
    created_at: string;
  }>;
  timeline: Array<{
    id: string;
    title: string;
    created_at: string;
  }>;
};

export type ProfileImpact = {
  current_level?: string | null;
  next_level?: string | null;
  confirmed_contributions_count: number;
  supported_campaigns_count: number;
  completed_supported_campaigns: number;
  active_supported_campaigns: number;
  fundraising_supported_campaigns: number;
  total_supported_amount: string;
  progress_percent: number;
  is_patron: boolean;
  patron_since?: string | null;
};

export type PlatformStats = {
  users_count: number;
  campaigns_total: number;
  campaigns_active: number;
  campaigns_completed: number;
  successful_reports: number;
  confirmed_contributions: number;
  total_donated_amount: string;
};

export type ContactSubject =
  | "Общий вопрос"
  | "Сообщить об ошибке"
  | "Предложение"
  | "Проблема со сбором"
  | "Другое";

export type ContactRequestInput = {
  name: string;
  email: string;
  telegram?: string;
  subject: ContactSubject;
  message: string;
};

export type UserAchievement = {
  code: string;
  title: string;
  description: string;
  unlocked_at: string;
};

export type CommunityPatron = {
  user_id: string;
  username: string;
  level: string;
  confirmed_contributions_count: number;
  supported_campaigns_count: number;
  total_donated_amount: string;
  patron_since: string;
  recent_supported_campaigns: Array<{
    id: string;
    title: string;
    cover_image_url?: string | null;
    last_supported_at: string;
  }>;
};

export type OwnerDashboard = {
  campaign?: CampaignListItem | null;
  campaigns_count: number;
  stats?: {
    contributions_count: number;
    unique_contributors_count: number;
    average_contribution: string;
    today_amount: string;
  } | null;
  recent_donations: RecentDonation[];
};

export type AuthUser = {
  id: string;
  username: string;
  email: string;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  bio?: string | null;
  city?: string | null;
  is_active: boolean;
  is_verified: boolean;
  role: "user" | "moderator" | "admin";
  created_at: string;
};

export type ProfileUpdateInput = {
  username?: string;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  bio?: string | null;
  city?: string | null;
};

export type ReportResponse = {
  id: string;
  campaign_id: string;
  reason: string;
  details?: string | null;
  status: "pending" | "reviewed" | "dismissed" | "action_taken";
  created_at: string;
};

export type AuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: AuthUser;
};

export type CampaignCreateInput = {
  title: string;
  description: string;
  target_amount: number;
  category: CampaignCategory;
  cover_image_url?: string | null;
};

export type CampaignUpdateInput = Partial<CampaignCreateInput>;

export type CampaignUpdateCreateInput = {
  title: string;
  content: string;
  photos: string[];
};

export type CampaignCompletionReport = {
  id: string;
  campaign_id: string;
  author_id: string;
  gratitude_text: string;
  created_at: string;
  raised_amount: string;
  supporters_count: number;
  photos: Array<{
    id: string;
    image_url: string;
    created_at: string;
  }>;
  supporters: Array<{
    name: string;
    is_anonymous: boolean;
  }>;
};

export type CampaignCompletionReportCreateInput = {
  gratitude_text: string;
  photos: string[];
};

export type CampaignCategory = "medical" | "education" | "emergency" | "pets" | "community" | "personal" | "other";

export type DonateResponse = {
  payment_id: string;
  status: "pending" | "succeeded" | "failed" | "canceled";
  anonymous_token?: string | null;
  subscription_created: boolean;
};

export type RecentDonation = {
  id: string;
  amount: string;
  username: string;
  created_at: string;
};

export type RecentDonationsPage = {
  items: RecentDonation[];
  has_more: boolean;
};

export type CampaignUpdatedEvent = {
  type: "campaign_updated";
  campaign_id: string;
  current_amount: string;
  goal_amount: string;
  progress_percentage: number;
  contributors_count: number;
  donation: RecentDonation;
};

export type PublicUserProfile = {
  id: string;
  username: string;
  first_name?: string | null;
  last_name?: string | null;
  avatar_url?: string | null;
  bio?: string | null;
  city?: string | null;
  created_at: string;
  supported_campaigns_count: number;
  total_supported_campaigns: number;
  total_donated_amount: string;
  created_campaigns_count: number;
  completed_campaigns_count: number;
  achievements_count: number;
  achievements: string[];
  campaigns_created: CampaignListItem[];
  author_reputation: AuthorReputation;
  is_verified: boolean;
};

export type ActivityItem = {
  id: string;
  type: "campaign_created" | "donation_made" | "campaign_completed" | "unlock_achieved";
  actor?: Owner | null;
  campaign?: { id: string; title: string } | null;
  metadata_json?: Record<string, unknown> | null;
  created_at: string;
};

export type NotificationItem = {
  id: string;
  type: "donation_received" | "campaign_funded" | "unlock_achieved" | "campaign_goal_reached" | "campaign_report_published" | "campaign_photos_added" | "campaign_author_update_created" | "achievement_unlocked" | "patron_unlocked" | "campaign_report_reminder" | "campaign_subscription_created" | "campaign_moderation";
  title: string;
  body: string;
  campaign_id?: string | null;
  action_url?: string | null;
  is_read: boolean;
  created_at: string;
};

export type CampaignLifecycleChangedEvent = {
  type: "campaign_lifecycle_changed";
  campaign_id: string;
  status: string;
};

export type CampaignRealtimeEvent = CampaignUpdatedEvent | CampaignLifecycleChangedEvent;

export type NotificationCreatedEvent = {
  type: "notification_created";
  notification: NotificationItem;
};

export type CampaignSubscription = {
  campaign_id: string;
  is_subscribed: boolean;
};

export type WithdrawalInfo = {
  campaign_id: string;
  available: boolean;
  mode: "demo";
};
