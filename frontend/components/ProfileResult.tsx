import type { ProfileResponse } from "@/lib/types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border-t border-slate-200 pt-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      {children}
    </div>
  );
}

export default function ProfileResult({ result }: { result: ProfileResponse }) {
  const data = result.data;
  if (!data) return null;

  return (
    <div className="flex flex-col gap-5 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      {result.partial && result.warnings.length > 0 && (
        <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          <p className="font-medium">Some data may be incomplete:</p>
          <ul className="mt-1 list-inside list-disc">
            {result.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex items-center gap-4">
        {data.profile_image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={data.profile_image_url}
            alt={data.name ?? "Profile"}
            className="h-16 w-16 rounded-full object-cover"
          />
        )}
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{data.name ?? "Unknown"}</h2>
          {data.headline && <p className="text-sm text-slate-600">{data.headline}</p>}
          {data.location && <p className="text-sm text-slate-400">{data.location}</p>}
        </div>
      </div>

      {data.about && (
        <Section title="About">
          <p className="whitespace-pre-line text-sm text-slate-700">{data.about}</p>
        </Section>
      )}

      {data.experience.length > 0 && (
        <Section title="Experience">
          <ul className="flex flex-col gap-3">
            {data.experience.map((exp, i) => (
              <li key={i} className="text-sm">
                <p className="font-medium text-slate-900">
                  {exp.title} {exp.company && <span className="font-normal text-slate-600">· {exp.company}</span>}
                </p>
                <p className="text-slate-400">
                  {[exp.duration, exp.location].filter(Boolean).join(" · ")}
                </p>
                {exp.description && <p className="mt-1 text-slate-600">{exp.description}</p>}
              </li>
            ))}
          </ul>
        </Section>
      )}

      {data.education.length > 0 && (
        <Section title="Education">
          <ul className="flex flex-col gap-3">
            {data.education.map((edu, i) => (
              <li key={i} className="text-sm">
                <p className="font-medium text-slate-900">{edu.institution}</p>
                <p className="text-slate-600">
                  {[edu.degree, edu.field_of_study].filter(Boolean).join(", ")}
                </p>
                <p className="text-slate-400">
                  {[edu.start_date, edu.end_date].filter(Boolean).join(" - ")}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {data.skills.length > 0 && (
        <Section title="Skills">
          <div className="flex flex-wrap gap-2">
            {data.skills.map((skill, i) => (
              <span key={i} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">
                {skill.name}
                {skill.endorsement_count ? ` · ${skill.endorsement_count}` : ""}
              </span>
            ))}
          </div>
        </Section>
      )}

      {data.certifications.length > 0 && (
        <Section title="Certifications">
          <ul className="flex flex-col gap-2">
            {data.certifications.map((cert, i) => (
              <li key={i} className="text-sm">
                <p className="font-medium text-slate-900">{cert.name}</p>
                <p className="text-slate-500">
                  {[cert.issuing_organization, cert.issue_date].filter(Boolean).join(" · ")}
                </p>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {data.languages.length > 0 && (
        <Section title="Languages">
          <ul className="flex flex-wrap gap-x-6 gap-y-1 text-sm text-slate-700">
            {data.languages.map((lang, i) => (
              <li key={i}>
                {lang.name}
                {lang.proficiency ? ` — ${lang.proficiency}` : ""}
              </li>
            ))}
          </ul>
        </Section>
      )}
    </div>
  );
}
