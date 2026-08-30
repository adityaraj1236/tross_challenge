export interface ExperienceItem {
  title: string | null;
  company: string | null;
  company_linkedin_url: string | null;
  company_logo_url: string | null;
  employment_type: string | null;
  location: string | null;
  start_date: string | null;
  end_date: string | null;
  duration: string | null;
  description: string | null;
}

export interface EducationItem {
  institution: string | null;
  institution_linkedin_url: string | null;
  institution_logo_url: string | null;
  degree: string | null;
  field_of_study: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface SkillItem {
  name: string;
  endorsement_count: number | null;
}

export interface CertificationItem {
  name: string | null;
  issuing_organization: string | null;
  issue_date: string | null;
  credential_id: string | null;
  credential_url: string | null;
}

export interface LanguageItem {
  name: string;
  proficiency: string | null;
}

export interface HonorItem {
  title: string | null;
  issuer: string | null;
  issue_date: string | null;
  description: string | null;
}

export interface ProjectItem {
  name: string | null;
  description: string | null;
  url: string | null;
  start_date: string | null;
  end_date: string | null;
}

export interface VolunteerItem {
  organization: string | null;
  role: string | null;
  cause: string | null;
  start_date: string | null;
  end_date: string | null;
  description: string | null;
}

export interface CourseItem {
  name: string | null;
  number: string | null;
}

export interface PublicationItem {
  title: string | null;
  publisher: string | null;
  publish_date: string | null;
  description: string | null;
  url: string | null;
}

export interface ProfileData {
  linkedin_url: string;
  public_id: string;
  name: string | null;
  headline: string | null;
  location: string | null;
  about: string | null;
  open_to_work: boolean;
  follower_count: number | null;
  profile_image_url: string | null;
  cover_image_url: string | null;
  experience: ExperienceItem[];
  education: EducationItem[];
  skills: SkillItem[];
  certifications: CertificationItem[];
  languages: LanguageItem[];
  honors: HonorItem[];
  projects: ProjectItem[];
  volunteer_experience: VolunteerItem[];
  courses: CourseItem[];
  publications: PublicationItem[];
  interests: string[];
}

export interface ProfileResponse {
  success: boolean;
  data: ProfileData | null;
  partial: boolean;
  warnings: string[];
  fetched_at: string;
}

export interface ApiErrorBody {
  success: false;
  error_code: string;
  message: string;
}
