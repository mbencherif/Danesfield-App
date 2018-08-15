#!/usr/bin/env python
# -*- coding: utf-8 -*-

##############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
##############################################################################

from girder.api import access
from girder.api.describe import autoDescribeRoute, Description
from girder.api.rest import Resource, getApiUrl, getCurrentToken
from girder.models.collection import Collection
from girder.models.folder import Folder
from girder.models.user import User

from ..models import workingSet
from ..request_info import RequestInfo
from ..workflow_manager import DanesfieldWorkflowManager


class ProcessingResource(Resource):
    """
    API endpoints to run Danesfield algorithm jobs.
    """
    def __init__(self):
        super(ProcessingResource, self).__init__()

        self.resourceName = 'processing'

        self.route('POST', ('process',), self.process)

    def _datasetsFolder(self):
        """
        Return the datasets folder document. Creates a collection and folder if necessary.
        """
        # FIXME: Folder is accessible only to admin
        adminUser = User().getAdmins().next()
        collection = Collection().createCollection(
            name='core3d', creator=adminUser, description='', public=True, reuseExisting=True)
        folder = Folder().createFolder(
            parent=collection, name='datasets', parentType='collection', public=False,
            creator=adminUser, reuseExisting=True)
        return folder

    @access.user
    @autoDescribeRoute(
        Description('Run the complete processing workflow.')
        .notes('Call this endpoint to run the complete processing workflow.\n\n'
               'Options may be provided for individual steps by passing a JSON object '
               'in the **options** parameter. For example:\n\n'
               '```\n'
               '{\n'
               '    "generate-point-cloud": {\n'
               '        "longitude": -84.084032161833051,\n'
               '        "latitude": 39.780404255857590,\n'
               '        "longitudeWidth": 0.008880209782049,\n'
               '        "latitudeWidth": 0.007791684155826\n'
               '    },\n'
               '    "fit-dtm": {\n'
               '        "iterations": 100,\n'
               '        "tension": 10\n'
               '    },\n'
               '    "orthorectify": {\n'
               '        "occlusionThreshold": 1.0,\n'
               '        "denoiseRadius": 2.0\n'
               '    }\n'
               '}\n'
               '```\n')
        .modelParam('workingSet', 'The ID of the working set.', model=workingSet.WorkingSet,
                    paramType='query')
        .jsonParam('options', 'Processing options keyed by step name.', requireObject=True,
                   required=False)
        .errorResponse()
        .errorResponse('Read access was denied on the item.', 403)
    )
    def process(self, workingSet, options, params):
        """
        Run the complete processing workflow.
        """
        user = self.getCurrentUser()
        apiUrl = getApiUrl()
        token = getCurrentToken()
        outputFolder = self._datasetsFolder()

        requestInfo = RequestInfo(user=user, apiUrl=apiUrl, token=token)

        workflowManager = DanesfieldWorkflowManager.instance()
        jobId = workflowManager.initJob(requestInfo, workingSet, outputFolder, options)
        DanesfieldWorkflowManager.instance().advance(jobId=jobId)
