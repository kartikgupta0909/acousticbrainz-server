from __future__ import absolute_import
from webserver.testing import ServerTestCase
from db import dataset, dataset_eval, user
from db.testing import TEST_DATA_PATH
from flask import url_for
import os.path
import json


class DatasetsViewsTestCase(ServerTestCase):

    def setUp(self):
        super(DatasetsViewsTestCase, self).setUp()

        self.test_user_mb_name = "tester"
        self.test_user_id = user.create(self.test_user_mb_name)

        self.test_uuid = "123e4567-e89b-12d3-a456-426655440000"
        self.test_mbid_1 = "e8afe383-1478-497e-90b1-7885c7f37f6e"
        self.test_mbid_2 = "0dad432b-16cc-4bf0-8961-fd31d124b01b"

        self.test_data = {
            "name": "Test",
            "description": "",
            "classes": [
                {
                    "name": "Class #1",
                    "description": "This is a description of class #1!",
                    "recordings": [
                        self.test_mbid_1,
                        self.test_mbid_2,
                    ]
                },
                {
                    "name": "Class #2",
                    "description": "",
                    "recordings": [
                        self.test_mbid_1,
                        self.test_mbid_2,
                    ]
                },
            ],
            "public": True,
        }

        # Loading the actual data because it is required to evaluate the dataset
        self.load_low_level_data(self.test_mbid_1)
        self.load_low_level_data(self.test_mbid_2)

    def test_view(self):
        resp = self.client.get(url_for("datasets.view", id=self.test_uuid))
        self.assert404(resp)

        dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        resp = self.client.get(url_for("datasets.view", id=dataset_id))
        self.assert200(resp)

    def test_view_json(self):
        resp = self.client.get(url_for("datasets.view_json", id=self.test_uuid))
        self.assert404(resp)

        dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)
        resp = self.client.get(url_for("datasets.view_json", id=dataset_id))
        self.assert200(resp)

        dataset_eval.evaluate_dataset(dataset_id)

        self.temporary_login(self.test_user_id)

    def test_eval_job_delete(self):
        resp = self.client.delete("/datasets/%s/%s" % (self.test_uuid, self.test_uuid))
        self.assert404(resp)

        dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        resp = self.client.delete("/datasets/%s/%s" % (dataset_id, self.test_uuid))
        self.assert404(resp)

        job_id = dataset_eval.evaluate_dataset(dataset_id)

        resp = self.client.delete("/datasets/%s/%s" % (dataset_id, job_id))
        self.assert401(resp)

        # As an author
        self.temporary_login(self.test_user_id)
        resp = self.client.delete("/datasets/%s/%s" % (dataset_id, job_id))
        self.assert200(resp)

        self.assertIsNone(dataset_eval.get_job(job_id))

    def test_create(self):
        resp = self.client.get(url_for("datasets.create"))
        self.assertStatus(resp, 302)

        resp = self.client.post(
            url_for("datasets.create"),
            headers={"Content-Type": "application/json"},
            data=json.dumps(self.test_data),
        )
        self.assertStatus(resp, 302)

        # With logged in user
        self.temporary_login(self.test_user_id)

        resp = self.client.get(url_for("datasets.create"))
        self.assert200(resp)

        resp = self.client.post(
            url_for("datasets.create"),
            headers={"Content-Type": "application/json"},
            data=json.dumps(self.test_data),
        )
        self.assert200(resp)
        self.assertTrue(len(dataset.get_by_user_id(self.test_user_id)) == 1)

    def test_edit(self):
        # Should redirect to login page even if trying to edit dataset that
        # doesn't exist.
        resp = self.client.get(url_for("datasets.edit", dataset_id=self.test_uuid))
        self.assertStatus(resp, 302)

        dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        # Trying to edit without login
        resp = self.client.get(url_for("datasets.edit", dataset_id=dataset_id))
        self.assertStatus(resp, 302)
        resp = self.client.post(
            url_for("datasets.edit", dataset_id=dataset_id),
            headers={"Content-Type": "application/json"},
            data=json.dumps(self.test_data),
        )
        self.assertStatus(resp, 302)

        # Editing using another user
        another_user_id = user.create("another_tester")
        self.temporary_login(another_user_id)
        resp = self.client.get(url_for("datasets.edit", dataset_id=dataset_id))
        self.assert401(resp)
        resp = self.client.post(
            url_for("datasets.edit", dataset_id=dataset_id),
            headers={"Content-Type": "application/json"},
            data=json.dumps(self.test_data),
        )
        self.assert401(resp)

        # Editing properly
        self.temporary_login(self.test_user_id)
        resp = self.client.get(url_for("datasets.edit", dataset_id=dataset_id))
        self.assert200(resp)
        resp = self.client.post(
            url_for("datasets.edit", dataset_id=dataset_id),
            headers={"Content-Type": "application/json"},
            data=json.dumps(self.test_data),
        )
        self.assert200(resp)

    def test_delete(self):
        # Should redirect to login page even if trying to delete dataset that
        # doesn't exist.
        resp = self.client.get(url_for("datasets.delete", dataset_id=self.test_uuid))
        self.assertStatus(resp, 302)

        dataset_id = dataset.create_from_dict(self.test_data, author_id=self.test_user_id)

        # Trying to delete without login
        resp = self.client.get(url_for("datasets.delete", dataset_id=dataset_id))
        self.assertStatus(resp, 302)
        resp = self.client.post(url_for("datasets.delete", dataset_id=dataset_id))
        self.assertStatus(resp, 302)
        self.assertTrue(len(dataset.get_by_user_id(self.test_user_id)) == 1)

        # Deleting using another user
        another_user_id = user.create("another_tester")
        self.temporary_login(another_user_id)
        resp = self.client.get(url_for("datasets.delete", dataset_id=dataset_id))
        self.assert401(resp)
        resp = self.client.post(url_for("datasets.delete", dataset_id=dataset_id))
        self.assert401(resp)
        self.assertTrue(len(dataset.get_by_user_id(self.test_user_id)) == 1)

        # Editing properly
        self.temporary_login(self.test_user_id)
        resp = self.client.get(url_for("datasets.delete", dataset_id=dataset_id))
        self.assert200(resp)
        resp = self.client.post(url_for("datasets.delete", dataset_id=dataset_id))
        self.assertRedirects(resp, url_for("user.profile", musicbrainz_id=self.test_user_mb_name))
        self.assertTrue(len(dataset.get_by_user_id(self.test_user_id)) == 0)

    def test_recording_info(self):
        recording_mbid = "770cc467-8dde-4d22-bc4c-a42f91e7515e"

        resp = self.client.get(url_for("datasets.recording_info", mbid=recording_mbid))
        self.assertStatus(resp, 302)
        resp = self.client.get(url_for("datasets.recording_info", mbid=self.test_uuid))
        self.assertStatus(resp, 302)

        # With logged in user
        self.temporary_login(self.test_user_id)

        resp = self.client.get(url_for("datasets.recording_info", mbid=recording_mbid))
        self.assert200(resp)
        resp = self.client.get(url_for("datasets.recording_info", mbid=self.test_uuid))
        self.assert404(resp)
