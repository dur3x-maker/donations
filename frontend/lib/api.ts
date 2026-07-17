import type { ActivityItem, AuthResponse, AuthUser, AuthorReputation, BankAccountApplication, BankAccountApplicationState, CampaignCompletionReport, CampaignCompletionReportCreateInput, CampaignCreateInput, CampaignDetail, CampaignListItem, CampaignSubscription, CampaignUpdateCreateInput, CampaignUpdateInput, CampaignUpdateItem, CommunityPatron, CompletedCampaignListItem, ContactRequestInput, ContributionProgress, DonateResponse, NotificationItem, OwnerDashboard, PlatformStats, ProfileImpact, ProfileSummary, ProfileUpdateInput, PublicUserProfile, RecentDonationsPage, ReportResponse, UserAchievement, WithdrawalInfo } from "./types";
import { assertValidImage, MAX_IMAGE_SIZE_MB } from "./image-upload";

const browserApiUrl = normalizeApiUrl(process.env.NEXT_PUBLIC_API_URL, "NEXT_PUBLIC_API_URL");
const serverApiUrl = normalizeApiUrl(process.env.INTERNAL_API_URL ?? browserApiUrl, "INTERNAL_API_URL");
const ACCESS_TOKEN_KEY = "access_token";
const REFRESH_TOKEN_KEY = "refresh_token";
const AUTH_USER_KEY = "auth_user";

export function getApiUrl() {
  return typeof window === "undefined" ? serverApiUrl : browserApiUrl;
}

function normalizeApiUrl(value: string | undefined, name: string) {
  if (!value) {
    if (process.env.NODE_ENV === "production") {
      throw new Error(`${name} is required in production`);
    }
    return "http://localhost:8000";
  }

  const url = new URL(value);
  if (process.env.NODE_ENV === "production" && url.protocol !== "https:" && !isLocalRuntimeHost(url.hostname)) {
    throw new Error(`${name} must use https in production`);
  }
  url.pathname = url.pathname.replace(/\/+$/, "");
  return url.toString().replace(/\/$/, "");
}

function isLocalRuntimeHost(hostname: string) {
  return hostname === "localhost" || hostname === "127.0.0.1" || hostname === "backend";
}

export function getStoredAccessToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function getStoredRefreshToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
}

export function getStoredUser() {
  if (typeof window === "undefined") return null;
  const rawUser = localStorage.getItem(AUTH_USER_KEY);
  if (!rawUser) return null;

  try {
    const user = JSON.parse(rawUser) as AuthUser;
    if (hasMojibake(user.username) || hasMojibake(user.email)) {
      localStorage.removeItem(AUTH_USER_KEY);
      return null;
    }
    return user;
  } catch {
    clearStoredAuth();
    return null;
  }
}

export function saveAuth(auth: AuthResponse) {
  localStorage.setItem(ACCESS_TOKEN_KEY, auth.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, auth.refresh_token);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(auth.user));
}

function hasMojibake(value: string) {
  return /[РС][\u0400-\u045f]|[\u0400-\u045f][РС]|Р[а-яё]|С[а-яё]/i.test(value);
}

export function clearStoredAuth() {
  if (typeof window === "undefined") return;
  localStorage.removeItem(ACCESS_TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
}

async function refreshStoredAuth() {
  const refreshToken = getStoredRefreshToken();
  if (!refreshToken) return null;

  let response: Response;
  try {
    response = await fetch(`${getApiUrl()}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
  } catch {
    return null;
  }

  if (!response.ok) return null;

  const auth = (await response.json()) as AuthResponse;
  saveAuth(auth);
  window.dispatchEvent(new CustomEvent("auth:updated", { detail: auth.user }));
  return auth.access_token;
}

function redirectToLogin() {
  clearStoredAuth();
  window.dispatchEvent(new Event("auth:logout"));
  if (window.location.pathname !== "/login") {
    window.location.href = `/login?next=${encodeURIComponent(window.location.pathname)}`;
  }
}

type RequestOptions = {
  retry?: boolean;
  includeAuth?: boolean;
};

export async function request<T>(path: string, init?: RequestInit, options: RequestOptions = {}): Promise<T> {
  const { retry = true, includeAuth = true } = options;
  const headers = new Headers(init?.headers);
  if (!headers.has("Content-Type") && init?.body) {
    headers.set("Content-Type", "application/json");
  }

  const accessToken = getStoredAccessToken();
  if (includeAuth && accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  let response: Response;
  try {
    response = await fetch(`${getApiUrl()}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch {
    throw new Error("Не получилось связаться с сервером. Проверьте соединение и попробуйте еще раз.");
  }

  if (response.status === 401 && includeAuth && retry && typeof window !== "undefined") {
    const newAccessToken = await refreshStoredAuth();
    if (newAccessToken) {
      return request<T>(path, init, { retry: false, includeAuth });
    }
    redirectToLogin();
  }

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json() as Promise<T>;
}

async function readErrorMessage(response: Response) {
  if (response.status === 413) {
    return `Фото слишком большое. Максимальный размер — ${MAX_IMAGE_SIZE_MB} МБ.`;
  }

  let message = `Запрос не удался: ${response.status}`;

  try {
    const data = await response.clone().json();
    if (typeof data?.detail === "string") {
      message = data.detail;
    }
  } catch {
    const text = await response.text().catch(() => "");
    if (text) message = text;
  }

  return message;
}

export function fetchCampaigns(params?: { page?: number; page_size?: number; sort?: "newest" | "oldest" | "most_funded" | "least_funded"; q?: string }) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.sort) searchParams.set("sort", params.sort);
  if (params?.q) searchParams.set("q", params.q);
  const query = searchParams.toString();
  return request<CampaignListItem[]>(`/api/v1/campaigns${query ? `?${query}` : ""}`);
}

export function fetchCompletedCampaigns(params?: { page?: number; page_size?: number; q?: string }) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.q) searchParams.set("q", params.q);
  const query = searchParams.toString();
  return request<CompletedCampaignListItem[]>(`/api/v1/campaigns/completed${query ? `?${query}` : ""}`);
}

export function fetchPlatformStats() {
  return request<PlatformStats>("/api/v1/platform/stats");
}

export function fetchFeaturedCampaign() {
  return request<CampaignListItem | null>("/api/v1/platform/featured-campaign");
}

export function sendContactRequest(body: ContactRequestInput) {
  return request<{ ok: boolean; message: string }>("/api/v1/contact", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchCampaign(id: string) {
  return request<CampaignDetail>(`/api/v1/campaigns/${id}`);
}

export function fetchCampaignSubscription(campaignId: string) {
  return request<CampaignSubscription>(`/api/v1/campaigns/${campaignId}/subscription`);
}

export function fetchWithdrawalInfo(campaignId: string) {
  return request<WithdrawalInfo>(`/api/v1/campaigns/${campaignId}/withdrawal-info`);
}

export function subscribeToCampaign(campaignId: string) {
  return request<CampaignSubscription>(`/api/v1/campaigns/${campaignId}/subscription`, { method: "POST" });
}

export function unsubscribeFromCampaign(campaignId: string) {
  return request<CampaignSubscription>(`/api/v1/campaigns/${campaignId}/subscription`, { method: "DELETE" });
}

export function fetchRecentDonations(campaignId: string, params?: { offset?: number; limit?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const query = searchParams.toString();
  return request<RecentDonationsPage>(`/api/v1/campaigns/${campaignId}/recent-donations${query ? `?${query}` : ""}`);
}

export function fetchCampaignUpdates(campaignId: string) {
  return request<CampaignUpdateItem[]>(`/api/v1/campaigns/${campaignId}/updates`);
}

export function createCampaignUpdate(campaignId: string, body: CampaignUpdateCreateInput) {
  return request<CampaignUpdateItem>(`/api/v1/campaigns/${campaignId}/updates`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchCompletionReport(campaignId: string) {
  return request<CampaignCompletionReport>(`/api/v1/campaigns/${campaignId}/completion-report`);
}

export function createCompletionReport(campaignId: string, body: CampaignCompletionReportCreateInput) {
  return request<CampaignCompletionReport>(`/api/v1/campaigns/${campaignId}/completion-report`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchPublicProfile(username: string) {
  return request<PublicUserProfile>(`/api/v1/users/${username}`);
}

export function fetchAuthorReputation(userId: string) {
  return request<AuthorReputation>(`/api/v1/users/${userId}/reputation`);
}

export function fetchActivityFeed(params?: { page?: number; page_size?: number }) {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  const query = searchParams.toString();
  return request<ActivityItem[]>(`/api/v1/activity/feed${query ? `?${query}` : ""}`);
}

export function fetchNotifications() {
  return request<NotificationItem[]>("/api/v1/me/notifications");
}

export function markNotificationRead(notificationId: string) {
  return request<NotificationItem>(`/api/v1/me/notifications/${notificationId}/read`, { method: "POST" });
}

export function markNotificationsRead(notificationIds: string[]) {
  return request<{ updated_count: number }>("/api/v1/me/notifications/read", {
    method: "POST",
    body: JSON.stringify({ notification_ids: notificationIds }),
  });
}

export function createCampaign(body: CampaignCreateInput) {
  return request<CampaignDetail>("/api/v1/campaigns", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function uploadCampaignCover(file: File) {
  assertValidImage(file);
  const formData = new FormData();
  formData.append("file", file);

  const headers = new Headers();
  const accessToken = getStoredAccessToken();
  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const response = await fetch(`${getApiUrl()}/api/v1/uploads/campaign-cover`, {
    method: "POST",
    headers,
    body: formData,
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return response.json() as Promise<{ url: string }>;
}

export async function uploadStoryPhoto(file: File) {
  assertValidImage(file);
  const formData = new FormData();
  formData.append("file", file);
  const headers = new Headers();
  const accessToken = getStoredAccessToken();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${getApiUrl()}/api/v1/uploads/story-photo`, {
    method: "POST",
    headers,
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return response.json() as Promise<{ url: string }>;
}

export async function uploadAvatar(file: File) {
  assertValidImage(file);
  const formData = new FormData();
  formData.append("file", file);
  const headers = new Headers();
  const accessToken = getStoredAccessToken();
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const response = await fetch(`${getApiUrl()}/api/v1/uploads/avatar`, {
    method: "POST",
    headers,
    body: formData,
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await readErrorMessage(response));
  return response.json() as Promise<{ url: string }>;
}

export function updateProfile(body: ProfileUpdateInput) {
  return request<AuthUser>("/api/v1/me", {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function updateCampaign(campaignId: string, body: CampaignUpdateInput) {
  return request<CampaignDetail>(`/api/v1/campaigns/${campaignId}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function donate(campaignId: string, body: { amount: number; anonymous_token?: string }, options?: { anonymously?: boolean }) {
  return request<DonateResponse>(`/api/v1/campaigns/${campaignId}/donate`, {
    method: "POST",
    body: JSON.stringify(body),
  }, { includeAuth: !options?.anonymously });
}

export function reportCampaign(campaignId: string, body: { reason: string; details?: string }) {
  return request<ReportResponse>(`/api/v1/campaigns/${campaignId}/report`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchContributionProgress() {
  return request<ContributionProgress>("/api/v1/me/contribution-progress");
}

export function fetchOwnerDashboard() {
  return request<OwnerDashboard>("/api/v1/me/dashboard");
}

export function fetchBankAccountApplicationState() {
  return request<BankAccountApplicationState>("/api/v1/bank-account/application");
}

export function createBankAccountApplication() {
  return request<BankAccountApplication>("/api/v1/bank-account/applications", { method: "POST" });
}

export function fetchProfileSummary() {
  return request<ProfileSummary>("/api/v1/me/profile-summary");
}

export function fetchProfileImpact() {
  return request<ProfileImpact>("/api/v1/me/profile-impact");
}

export function fetchUserAchievements() {
  return request<UserAchievement[]>("/api/v1/me/achievements");
}

export function fetchCommunityPatrons() {
  return request<CommunityPatron[]>("/api/v1/community/patrons");
}

export function fetchCurrentUser() {
  return request<AuthUser>("/api/v1/auth/me", { method: "POST" });
}

export function verifyEmail(token: string) {
  return request<AuthUser>("/api/v1/auth/verify-email", {
    method: "POST",
    body: JSON.stringify({ token }),
  }, { retry: false });
}

export function resendEmailVerification() {
  return request<AuthUser>("/api/v1/auth/email-verification", { method: "POST" });
}

export function forgotPassword(email: string) {
  return request<{ message: string }>("/api/v1/auth/forgot-password", {
    method: "POST",
    body: JSON.stringify({ email }),
  }, { retry: false });
}

export function resetPassword(body: { token: string; password: string }) {
  return request<AuthResponse>("/api/v1/auth/reset-password", {
    method: "POST",
    body: JSON.stringify(body),
  }, { retry: false });
}

export function loginRequest(body: { email: string; password: string }) {
  return request<AuthResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  }, { retry: false });
}

export function registerRequest(body: { email: string; username: string; password: string }) {
  return request<AuthResponse>("/api/v1/auth/register", {
    method: "POST",
    body: JSON.stringify(body),
  }, { retry: false });
}

export function linkAnonymousContributions(anonymousToken: string) {
  return request<{ linked_count: number }>("/api/v1/me/link-anonymous-contributions", {
    method: "POST",
    body: JSON.stringify({ anonymous_token: anonymousToken }),
  });
}
