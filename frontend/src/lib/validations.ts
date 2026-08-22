import { z } from "zod";

export const loginSchema = z.object({
  email: z.string().email("Invalid email address"),
  password: z.string().min(6, "Password must be at least 6 characters"),
});

export const registerSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(100),
  email: z.string().email("Invalid email address"),
  password: z
    .string()
    .min(8, "Password must be at least 8 characters")
    .regex(/[A-Z]/, "Password must contain at least one uppercase letter")
    .regex(/[0-9]/, "Password must contain at least one number"),
  confirmPassword: z.string(),
  role: z.enum(["student", "teacher", "admin"]),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

export const subjectSchema = z.object({
  name: z.string().min(2, "Name must be at least 2 characters").max(100),
  description: z.string().min(5, "Description must be at least 5 characters").max(500),
});

export const examSchema = z.object({
  title: z.string().min(3, "Title must be at least 3 characters").max(200),
  description: z.string().max(1000).optional(),
  subject_id: z.number().positive("Please select a subject"),
  total_marks: z.number().min(1, "Total marks must be at least 1").max(1000),
  time_limit_minutes: z.number().min(5, "Minimum 5 minutes").max(300, "Maximum 5 hours"),
  available_from: z.string().optional(),
  available_until: z.string().optional(),
  is_active: z.boolean().optional(),
}).refine(
  (data) => !data.available_from || !data.available_until || data.available_until > data.available_from,
  { message: "End date must be after start date", path: ["available_until"] }
);

export const questionSchema = z.object({
  question_text: z.string().min(10, "Question must be at least 10 characters").max(2000),
  model_answer: z.string().min(5, "Model answer must be at least 5 characters").max(5000),
  marks: z.number().min(1, "Marks must be at least 1").max(100),
  keywords: z.array(z.string().min(1)).min(1, "Add at least one keyword").max(50),
});

export const answerSchema = z.object({
  question_id: z.number().positive(),
  answer_text: z
    .string()
    .min(1, "Answer cannot be empty")
    .max(10000, "Answer is too long"),
});

export type LoginFormData = z.infer<typeof loginSchema>;
export type RegisterFormData = z.infer<typeof registerSchema>;
export type SubjectFormData = z.infer<typeof subjectSchema>;
export type ExamFormData = z.infer<typeof examSchema>;
export type QuestionFormData = z.infer<typeof questionSchema>;
export type AnswerFormData = z.infer<typeof answerSchema>;
