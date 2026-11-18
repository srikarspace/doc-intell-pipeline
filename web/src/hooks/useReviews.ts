import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { deleteReview, postReview, type ReviewInput, type ReviewSaved } from "../lib/api.ts";
import type { Reviews } from "../lib/reviews.ts";

/**
 * The reviews of one answer. The server is the source of truth: a review shows only after the API saved it.
 * The work screen is keyed by the job, so a new contract starts with no reviews.
 */
export function useReviews(onSaved?: (reviews: Reviews) => void) {
  const [reviews, setReviews] = useState<Reviews>({});

  const save = useMutation({
    mutationFn: (body: ReviewInput) => postReview(body),
    onSuccess: (saved) => {
      const nextReviews = { ...reviews, [saved.field]: saved };
      setReviews(nextReviews);
      onSaved?.(nextReviews);
    },
  });

  const undo = useMutation({
    mutationFn: (review: ReviewSaved) => deleteReview(review.review_id),
    onSuccess: (_, review) =>
      setReviews((all) => {
        const { [review.field]: _gone, ...rest } = all;
        return rest;
      }),
  });

  /** The error of the last save or undo of this field, if it failed. */
  const errorFor = (field: string): string | null => {
    if (save.isError && save.variables?.field === field) return save.error.message;
    if (undo.isError && undo.variables?.field === field) return undo.error.message;
    return null;
  };

  return { reviews, save, undo, errorFor, busy: save.isPending || undo.isPending };
}
