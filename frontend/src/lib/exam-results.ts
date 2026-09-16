import { answersApi, MAX_PAGE_SIZE } from "@/lib/api";
import type { Answer, Exam } from "@/types";

export interface MyExamResult {
  totalScore: number;
  answeredCount: number;
}

/** Safety cap on pages of `MAX_PAGE_SIZE` we walk per exam. */
const MAX_PAGES = 5;

/**
 * Collect the signed-in student's own answers for a set of exams.
 *
 * Uses one targeted request per exam (`/answers/my-answers?exam_id=<id>`) with
 * server-side pagination, instead of downloading every answer the student ever
 * submitted and joining it in the browser. Exams with no answers are omitted.
 */
export async function fetchMyResultsByExam(
  exams: Exam[]
): Promise<Map<number, MyExamResult>> {
  const results = new Map<number, MyExamResult>();

  await Promise.all(
    exams.map(async (exam) => {
      let totalScore = 0;
      let answeredCount = 0;
      try {
        for (let page = 1; page <= MAX_PAGES; page++) {
          const res = await answersApi.getMyAnswers({
            exam_id: exam.id,
            page,
            size: MAX_PAGE_SIZE,
          });
          const batch: Answer[] = res.data.items ?? [];
          for (const answer of batch) {
            answeredCount += 1;
            totalScore += answer.score?.total_score || 0;
          }
          if (batch.length < MAX_PAGE_SIZE) break;
        }
      } catch {
        // Not accessible / transient failure: treat this exam as not answered.
        return;
      }
      if (answeredCount > 0) {
        results.set(exam.id, { totalScore, answeredCount });
      }
    })
  );

  return results;
}
