"""Tests for tender-product-analysis job cancel."""

import unittest

from tender_product_analysis.jobs import ProductJob, create_job, get_job, is_cancel_requested, request_cancel


class TestProductJobCancel(unittest.TestCase):
    def test_request_cancel_flags_job(self):
        job = ProductJob(id="testjob123456")
        from tender_product_analysis import jobs as jobs_mod

        with jobs_mod._lock:
            jobs_mod._jobs[job.id] = job
        job.status = "running"
        self.assertTrue(request_cancel(job.id))
        self.assertTrue(is_cancel_requested(job.id))
        self.assertFalse(request_cancel(job.id))
        with jobs_mod._lock:
            jobs_mod._jobs.pop(job.id, None)


if __name__ == "__main__":
    unittest.main()
