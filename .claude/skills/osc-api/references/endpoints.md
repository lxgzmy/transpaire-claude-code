# OSC API endpoints (generated — do not edit by hand)

Built from the OSCAPI OpenAPI spec, version `v7.3`.
Regenerate with `scripts/generate_endpoints.py` (see its docstring).
Host and credentials are configuration (`OSC_*` env), never recorded here.

`[WRITE]` marks operations that change the system of record — those go
through `osc_write`, which is gated (see SKILL.md).

## Alerts

- `GET /api/Alerts/Documents` — Gets the Alert Documents that match the OData filter criteria.
- `GET /api/Alerts/{AlertID}/Recipients/{RecipientID}` — Gets the Alert Recipient. (params: AlertID, RecipientID)
- **[WRITE]** `PUT /api/Alerts/{AlertID}/Recipients/{RecipientID}` — Creates or updates the Alert Recipient. (params: AlertID, RecipientID) (json body)

## ClientLogs

- **[WRITE]** `POST /api/ClientLogs` — Accepts a batch of client-side log entries from a client application and saves them to a per-source log file. (json body)

## ClientWorkflowActivities

- `GET /api/ClientWorkflowActivities/{ClientWorkflowActivityID}/Alerts` — Gets the Client Workflow Activity's Alerts that match the OData filter criteria. (params: ClientWorkflowActivityID)
- **[WRITE]** `POST /api/ClientWorkflowActivities/{ClientWorkflowActivityID}/Alerts` — Creates a Client Workflow Activity Alert. (params: ClientWorkflowActivityID) (json body)
- `GET /api/ClientWorkflowActivities/{ClientWorkflowActivityID}/Messages` — Gets the Client Workflow Activity's Messages that match the OData filter criteria. (params: ClientWorkflowActivityID)
- **[WRITE]** `POST /api/ClientWorkflowActivities/{ClientWorkflowActivityID}/Messages` — Creates a Client Workflow Activity Message. (params: ClientWorkflowActivityID) (json body)

## ClientWorkflows

- `GET /api/ClientWorkflows/{ClientWorkflowID}` — Gets the Client Workflow. (params: ClientWorkflowID)
- `GET /api/ClientWorkflows/{ClientWorkflowID}/Activities` — Gets the Client Workflow's Activities that match the OData filter criteria. (params: ClientWorkflowID)

## Clients

- **[WRITE]** `POST /api/Clients` — Creates a Client. (json body)
- `GET /api/Clients` — Gets the Clients that match the OData filter criteria.
- `GET /api/Clients/Contacts` — Gets all the Client Contacts that match the OData filter criteria.
- **[WRITE]** `PATCH /api/Clients/{ClientID}` — Updates a Client. (params: ClientID) (json body)
- **[WRITE]** `POST /api/Clients/{ClientID}/Contacts/{PersonID}` — Creates a Client Contact. (params: ClientID, PersonID) (json body)
- **[WRITE]** `DELETE /api/Clients/{ClientID}/Contacts/{PersonID}` — Deletes a Client Contact. (params: ClientID, PersonID)
- **[WRITE]** `PATCH /api/Clients/{ClientID}/Contacts/{PersonID}` — Updates a Client Contact. (params: ClientID, PersonID) (json body)

## DefectCategories

- `GET /api/DefectCategories` — Gets the Defect Categories that match the OData filter criteria.
- `GET /api/DefectCategories/Defaults` — Gets the default Defect Categories.

## Defects

- `GET /api/Defects` — Gets all Defects that match the OData filter criteria.
- `GET /api/Defects/Alerts` — Gets the Defect Alerts that match the OData filter criteria.
- **[WRITE]** `PATCH /api/Defects/{DefectID}` — Updates a Defect. (params: DefectID) (json body)
- **[WRITE]** `POST /api/Defects/{DefectID}/Alerts` — Creates a Defect Alert. (params: DefectID) (json body)
- **[WRITE]** `POST /api/Defects/{DefectID}/AutoAssignServiceProvider` — Automatically assigns a Defect's Service Provider. (params: DefectID)
- **[WRITE]** `POST /api/Defects/{DefectID}/BookedStartConfirmation` — Confirms or unconfirms the Defect's Booked Start Date. (params: DefectID) (json body)
- **[WRITE]** `POST /api/Defects/{DefectID}/BookedStartDate` — Sets the Defect's Booked Start Date. (params: DefectID) (json body)
- **[WRITE]** `POST /api/Defects/{DefectID}/Complete` — Completes a Defect. (params: DefectID) (json body)
- **[WRITE]** `POST /api/Defects/{DefectID}/EmailWorkReleases` — Sends an Email Work Release and records it against the Defect. (params: DefectID, X-G-Token, X-MS-Token) (json body)
- `GET /api/Defects/{DefectID}/EmailWorkReleases/Template` — Retrieves and populates the Work Release Email Template applicable to the Defect. (params: DefectID)
- `GET /api/Defects/{DefectID}/Messages` — Gets the Defect's Messages that match the OData filter criteria. (params: DefectID)
- **[WRITE]** `POST /api/Defects/{DefectID}/Messages` — Creates a Defect Message. (params: DefectID) (json body)
- **[WRITE]** `POST /api/Defects/{DefectID}/NotApplicable` — Marks a Defect as Not Applicable. (params: DefectID)
- `GET /api/Defects/{DefectID}/ServiceProviders` — Gets the Service Providers that are assignable to the Defect and match the OData filter criteria. (params: DefectID)
- **[WRITE]** `POST /api/Defects/{DefectID}/WorkReleases` — Creates a Defect Work Release. (params: DefectID) (json body)
- `GET /api/Defects/{DefectID}/WorkReleases/AvailableAttachments` — Gets the Defect's available attachments. (params: DefectID)
- `GET /api/Defects/{DefectID}/WorkReleases/Default` — Gets a Default Work Release for the Defect. (params: DefectID)

## DocumentTypes

- `GET /api/DocumentTypes` — Gets all Document Types.
- `GET /api/DocumentTypes/Attachable` — Gets all Document Types the user can associate to a Document when attaching.

## Documents

- `GET /api/Documents/{DocumentID}/File` — Gets the Document's file. (params: DocumentID)
- **[WRITE]** `PATCH /api/Documents/{DocumentID}/Reversion` — Reversions a Document. (params: DocumentID) (json body)

## EmailAccounts

- `GET /api/EmailAccounts` — Gets all Email Accounts that match the OData filter criteria.
- **[WRITE]** `POST /api/EmailAccounts` — Creates an Email Account. (json body)
- `GET /api/EmailAccounts/Providers` — Gets all Email Providers.
- **[WRITE]** `DELETE /api/EmailAccounts/{EmailAccountID}` — Deletes an Email Account. (params: EmailAccountID)
- **[WRITE]** `PATCH /api/EmailAccounts/{EmailAccountID}` — Updates an Email Account. (params: EmailAccountID) (json body)

## InspectionAnswers

- **[WRITE]** `POST /api/InspectionAnswers/{InspectionAnswerID}` — Updates the Inspection Answer. (params: InspectionAnswerID) (json body)
- **[WRITE]** `DELETE /api/InspectionAnswers/{InspectionAnswerID}/Documents/{DocumentID}` — Deletes a Document from an Inspection Answer. (params: DocumentID, InspectionAnswerID)

## InspectionDefects

- **[WRITE]** `DELETE /api/InspectionDefects/{InspectionDefectID}` — Deletes an Inspection Defect. (params: inspectionDefectID)
- **[WRITE]** `POST /api/InspectionDefects/{InspectionDefectID}` — Updates an Inspection Defect. (params: InspectionDefectID) (json body)
- **[WRITE]** `DELETE /api/InspectionDefects/{InspectionDefectID}/Documents/{DocumentID}` — Deletes a Document from an Inspection Defect. (params: DocumentID, InspectionDefectID)

## InspectionTemplates

- `GET /api/InspectionTemplates` — Gets all Inspection Templates that match the OData filter criteria.

## Inspections

- `GET /api/Inspections` — Gets all the Inspections that match the OData filter criteria.
- **[WRITE]** `POST /api/Inspections/{InspectionID}` — Completes an Inspection. (params: InspectionID) (json body)
- `GET /api/Inspections/{InspectionID}/Answers` — Gets the Inspection Answers of an Inspection that match the OData filter criteria. (params: InspectionID)
- `GET /api/Inspections/{InspectionID}/CompletionDefects` — Gets all the Inspection Completion Defects that will be created when the selected Inspection is completed. (params: InspectionID)
- **[WRITE]** `POST /api/Inspections/{InspectionID}/InspectionDefects` — Creates an Inspection Defect on the Inspection. (params: InspectionID) (json body)
- `GET /api/Inspections/{InspectionID}/InspectionDefects` — Gets the Inspection's Defects that match the OData filter criteria. (params: InspectionID)

## JobActivities

- `GET /api/JobActivities` — Gets the Job Activities that match the OData filter criteria.
- `GET /api/JobActivities/Alerts` — Gets the Job Activity's Alerts that match the OData filter criteria.
- `GET /api/JobActivities/CompletionAnswerStates` — Gets the Completion Answer States that match the OData filter criteria.
- **[WRITE]** `PATCH /api/JobActivities/{JobActivityID}` — Updates a Job Activity. (params: JobActivityID) (json body)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/Alerts` — Creates a Job Activity Alert. (params: JobActivityID) (json body)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/BookedStartConfirmation` — Confirms or unconfirms the Job Activity's Booked Start Date. (params: JobActivityID) (json body)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/BookedStartDate` — Sets the Job Activity's Booked Start Date. (params: JobActivityID) (json body)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/Complete` — Completes a Job Activity. (params: JobActivityID) (json body)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/EmailWorkReleases` — Sends an Email Work Release and records it against the Job Activity. (params: X-G-Token, JobActivityID, X-MS-Token) (json body)
- `GET /api/JobActivities/{JobActivityID}/EmailWorkReleases/Template` — Retrieves and populates the Work Release Email Template applicable to the Job Activity. (params: JobActivityID)
- `GET /api/JobActivities/{JobActivityID}/Messages` — Gets the Job Activity's Messages that match the OData filter criteria. (params: JobActivityID)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/Messages` — Creates a Job Activity Message. (params: JobActivityID) (json body)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/NotApplicable` — Marks a Job Activity as Not Applicable. (params: JobActivityID) (json body)
- `GET /api/JobActivities/{JobActivityID}/Questions` — Gets the Job Activity's Completion Questions. (params: JobActivityID)
- **[WRITE]** `PUT /api/JobActivities/{JobActivityID}/Questions/{CompletionQuestionID}` — Creates or updates a Job Activity Completion Answer. (params: JobActivityID, CompletionQuestionID) (json body)
- `GET /api/JobActivities/{JobActivityID}/ServiceProviders` — Gets the Service Providers that are assignable to the Job Activity and match the OData filter criteria. (params: JobActivityID)
- **[WRITE]** `POST /api/JobActivities/{JobActivityID}/WorkReleases` — Creates a Job Activity Work Release. (params: JobActivityID) (json body)
- `GET /api/JobActivities/{JobActivityID}/WorkReleases/AvailableAttachments` — Gets the Job Activity's available attachments. (params: JobActivityID)
- `GET /api/JobActivities/{JobActivityID}/WorkReleases/Default` — Gets a default Work Release for the Job Activity. (params: JobActivityID)

## Jobs

- `GET /api/Jobs` — Gets the Jobs that match the OData filter criteria. (json body)
- **[WRITE]** `POST /api/Jobs` — Creates a Job. (json body)
- `GET /api/Jobs/Alerts` — Gets the Job Alerts that match the OData filter criteria.
- `GET /api/Jobs/Contacts` — Gets all the Job Contacts that match the OData filter criteria.
- `GET /api/Jobs/CustomFieldSchemas` — Gets the Job Custom Field Schemas that match the OData filter criteria.
- `GET /api/Jobs/CustomFields` — Gets the Job Custom Fields that match the OData filter criteria.
- `GET /api/Jobs/Documents` — Gets the Job Documents that match the OData filter criteria.
- `GET /api/Jobs/SubJobRelationships` — Gets the Sub Job Relationships that match the OData filter criteria.
- `GET /api/Jobs/WorkflowStatuses` — Gets the Job Workflow Statuses that match the OData filter criteria.
- `GET /api/Jobs/WorkflowTemplates` — Gets the Job Workflow Templates that match the filter criteria. (params: Name)
- **[WRITE]** `PATCH /api/Jobs/{JobID}` — Updates the Job. (params: JobID) (json body)
- **[WRITE]** `POST /api/Jobs/{JobID}/AddWorkflowTemplate` — Appends or inserts a Workflow Template to an existing Job Workflow. This endpoint is a remote procedure call. (params: JobID) (json body)
- **[WRITE]** `POST /api/Jobs/{JobID}/Alerts` — Creates a Job Alert. (params: JobID) (json body)
- **[WRITE]** `POST /api/Jobs/{JobID}/Contacts/{PersonID}` — Creates a Job Contact. (params: JobID, PersonID) (json body)
- **[WRITE]** `DELETE /api/Jobs/{JobID}/Contacts/{PersonID}` — Deletes the Job Contact. (params: JobID, PersonID)
- **[WRITE]** `PATCH /api/Jobs/{JobID}/Contacts/{PersonID}` — Updates the Job Contact. (params: JobID, PersonID) (json body)
- **[WRITE]** `PATCH /api/Jobs/{JobID}/Contract` — Updates the Job's Contract. (params: JobID) (json body)
- `GET /api/Jobs/{JobID}/Defects` — Gets the Job's Defects that match the OData filter criteria. (params: JobID)
- **[WRITE]** `POST /api/Jobs/{JobID}/Defects` — Creates a Defect. (params: JobID) (json body)
- `GET /api/Jobs/{JobID}/Defects/Locations` — Gets the Job's Defect Locations that match the OData filter criteria. (params: JobID)
- `GET /api/Jobs/{JobID}/DocumentTypes` — Gets the Document Types in use by Job Documents for the specified Job. (params: JobID)
- **[WRITE]** `POST /api/Jobs/{JobID}/Documents` — Adds Documents to the Job. (params: JobID) (json body)
- `GET /api/Jobs/{JobID}/Inspections` — Gets the Job's Inspections that match the OData filter criteria. (params: JobID)
- **[WRITE]** `POST /api/Jobs/{JobID}/Inspections` — Creates an Inspection from a Template. (params: JobID) (json body)
- `GET /api/Jobs/{JobID}/Locations` — Gets the Job's Locations that match the OData filter criteria. (params: JobID)
- `GET /api/Jobs/{JobID}/Messages` — Gets the Job's Messages that match the OData filter criteria. (params: JobID)
- **[WRITE]** `POST /api/Jobs/{JobID}/Messages` — Creates a Job Message. (params: JobID) (json body)
- `GET /api/Jobs/{JobID}/ServiceTypes/{ServiceTypeID}/ServiceProviders` — Gets the Service Providers that match the OData filter criteria that are assigned to Activities using the nominated Service Type on the Job. (params: JobID, ServiceTypeID)
- **[WRITE]** `POST /api/Jobs/{JobID}/SubJobs` — Creates a Sub Job. (params: JobID) (json body)
- `GET /api/Jobs/{JobID}/Variations` — Gets the Job's Variations that match the OData filter criteria. (params: JobID)
- **[WRITE]** `POST /api/Jobs/{JobID}/Variations` — Creates a Job Variation. (params: JobID) (json body)

## Liink

- **[WRITE]** `POST /api/Liink/DisableLiinkProcessor` — Attempts to disable Liink sync.
- `GET /api/Liink/DocumentTypes` — Gets UUIDs of the Liink Document Types.
- `GET /api/Liink/Jobs/{LiinkID}` — Gets the Job with the specified LiinkID. (params: LiinkID)
- `GET /api/Liink/ServiceProviders/{LiinkID}` — Gets the Service Provider with the specified LiinkID. (params: LiinkID)

## Locations

- `GET /api/Locations` — Gets the Locations that match the OData filter criteria. Locations are presented in default display order.

## Messages

- `GET /api/Messages/Documents` — Gets the Message Documents that match the OData filter criteria.

## Miscellaneous

- `GET /api/Miscellaneous/ContactDetailsPrimaryCommunicationMethods` — Gets all Primary Communication Methods for Contact Details.
- `GET /api/Miscellaneous/ContractCalculations` — Gets all Contract Calculations.
- `GET /api/Miscellaneous/EmailSignatures` — Gets the logged in User's Email Signatures.
- `GET /api/Miscellaneous/PreferredCommunicationGroups` — Gets all Preferred Communication Groups.
- `GET /api/Miscellaneous/RelationshipOptions` — Gets all Relationship Options.

## MobileApp

- `GET /api/MobileApp/ClientWorkflows` — Gets all Client Workflows that match the filter criteria. (params: DetailFilter, PagedInfo.PagedSortOn, PagedInfo.PagedSortOrder, PagedInfo.PageSize, PagedInfo.RequestedPage)
- `GET /api/MobileApp/ClientWorkflows/{ClientWorkflowID}/Contacts` — Gets the Client Workflow's Contacts that match the filter criteria. (params: ClientContactType, ClientWorkflowID, ContactName, PagedSortOn, PagedSortOrder, PageSize, RequestedPage)
- `GET /api/MobileApp/ClientWorkflows/{ClientWorkflowID}/Documents` — Gets the Client Workflow's Documents that have an image, video, PDF, Word, Excel, or Outlook extension. (params: ClientWorkflowID, PagedSortOn, PagedSortOrder, PageSize, RequestedPage)
- `GET /api/MobileApp/Jobs` — Gets the Jobs that match the filter criteria. (params: DetailFilter, PagingInstructions.PagedSortOn, PagingInstructions.PagedSortOrder, PagingInstructions.PageSize, PagingInstructions.RequestedPage, ShouldOnlyShowMyJobs, WorkflowStatusIDs)
- `GET /api/MobileApp/Jobs/{JobID}/Contacts` — Gets the Job's Contacts that match the filter criteria. (params: ContactName, JobContactType, JobID, PagedSortOn, PagedSortOrder, PageSize, RequestedPage)
- `GET /api/MobileApp/Jobs/{JobID}/Documents` — Gets the Job's Documents that have an image, video, PDF, Word, Excel, or Outlook extension. (params: JobID, PagedSortOn, PagedSortOrder, PageSize, RequestedPage)
- `GET /api/MobileApp/Messages/{MessageID}` — Gets the Message. (params: MessageID)
- `GET /api/MobileApp/Messages/{MessageID}/Documents` — Gets the Message's Documents that have an image, video, PDF, Word, Excel, or Outlook extension. (params: MessageID)
- **[WRITE]** `POST /api/MobileApp/Messages/{MessageID}/Replies` — Adds a Reply to the Message. (params: MessageID) (json body)

## OAuth

- **[WRITE]** `POST /api/Token` — Creates an OAuth Bearer Token. (json body)

## Orders

- `GET /api/Orders` — Gets all Orders that match the OData filter criteria.
- **[WRITE]** `POST /api/Orders` — Creates an Order. (json body)
- **[WRITE]** `DELETE /api/Orders/{OrderID}` — Deletes the Order. (params: OrderID)
- **[WRITE]** `PATCH /api/Orders/{OrderID}` — Updates the Order. (params: OrderID) (json body)
- `GET /api/Orders/{OrderID}/File` — Gets the file associated with the Order. (params: OrderID)

## Persons

- `GET /api/Persons` — Gets the Persons that match the OData filter criteria.
- **[WRITE]** `POST /api/Persons` — Creates a Person. (json body)
- `GET /api/Persons/CustomFieldSchemas` — Gets the Person Custom Field Schemas that match the OData filter criteria.
- `GET /api/Persons/CustomFields` — Gets the Person Custom Fields that match the OData filter criteria.
- **[WRITE]** `DELETE /api/Persons/{PersonID}` — Deletes a Person. (params: PersonID)
- **[WRITE]** `PATCH /api/Persons/{PersonID}` — Updates a Person. (params: PersonID) (json body)

## Regions

- `GET /api/Regions` — Gets all Regions that match the OData filter criteria.

## ServiceProviders

- **[WRITE]** `POST /api/ServiceProviders` — Creates a Service Provider. (json body)
- `GET /api/ServiceProviders` — Gets the Service Providers that match the OData filter criteria.
- `GET /api/ServiceProviders/Contacts` — Gets all the Service Provider Contacts that match the OData filter criteria.
- `GET /api/ServiceProviders/CustomFieldSchemas` — Gets the Service Provider Custom Field Schemas that match the OData filter criteria.
- `GET /api/ServiceProviders/CustomFields` — Gets the Service Provider Custom Fields that match the OData filter criteria.
- `GET /api/ServiceProviders/EntityTypes` — Gets the Service Provider Entity Types that match the OData filter criteria.
- `GET /api/ServiceProviders/Regions` — Gets all Service Provider Regions that match the OData filter criteria.
- `GET /api/ServiceProviders/ServiceTypes` — Gets all Service Provider Service Types that match the OData filter criteria.
- `GET /api/ServiceProviders/StatutoryRequirements` — Gets all the Service Provider Statutory Requirements that match the OData filter criteria.
- **[WRITE]** `PATCH /api/ServiceProviders/{ServiceProviderID}` — Updates a Service Provider. (params: ServiceProviderID) (json body)
- **[WRITE]** `POST /api/ServiceProviders/{ServiceProviderID}/Contacts/{PersonID}` — Creates a Service Provider Contact. (params: ServiceProviderID, PersonID) (json body)
- **[WRITE]** `DELETE /api/ServiceProviders/{ServiceProviderID}/Contacts/{PersonID}` — Deletes a Service Provider's Contact. (params: PersonID, ServiceProviderID)
- **[WRITE]** `PATCH /api/ServiceProviders/{ServiceProviderID}/Contacts/{PersonID}` — Updates a Service Provider Contact. (params: ServiceProviderID, PersonID) (json body)
- `GET /api/ServiceProviders/{ServiceProviderID}/DefectWorkReleaseContacts/{DefectID}` — Gets the Defect Work Release Contacts of the Service Provider. (params: DefectID, ServiceProviderID)
- **[WRITE]** `POST /api/ServiceProviders/{ServiceProviderID}/Documents` — Adds a Document to the Service Provider. (params: ServiceProviderID) (json body)
- `GET /api/ServiceProviders/{ServiceProviderID}/JobActivityWorkReleaseContacts/{JobActivityID}` — Gets the Job Activity Work Release Contacts of the Service Provider. (params: JobActivityID, ServiceProviderID)
- **[WRITE]** `PUT /api/ServiceProviders/{ServiceProviderID}/StatutoryRequirements/{StatutoryRequirementID}` — Creates or updates the Service Provider Statutory Requirement. (params: ServiceProviderID, StatutoryRequirementID) (json body)
- **[WRITE]** `DELETE /api/ServiceProviders/{ServiceProviderID}/StatutoryRequirements/{StatutoryRequirementID}` — Deletes a Service Provider Statutory Requirement. (params: ServiceProviderID, StatutoryRequirementID)

## ServiceTypes

- `GET /api/ServiceTypes` — Gets the Service Types that match the OData filter criteria.
- **[WRITE]** `POST /api/ServiceTypes` — Creates a Service Type. (json body)
- **[WRITE]** `PATCH /api/ServiceTypes/{ServiceTypeID}` — Updates a Service Type. (params: ServiceTypeID) (json body)
- `GET /api/ServiceTypes/{ServiceTypeID}/ServiceProviders` — Gets the Service Providers associated with a given Service Type that match the OData filter criteria. (params: ServiceTypeID)

## Services

- `GET /api/Services` — Gets all Services that match the OData filter criteria.

## StatutoryRequirements

- `GET /api/StatutoryRequirements` — Gets the Statutory Requirements that match the OData filter criteria. Presented in the default display order.

## StoppageRequests

- **[WRITE]** `POST /api/StoppageRequests` — Creates a Stoppage Request. (json body)
- `GET /api/StoppageRequests/Reasons` — Gets the Stoppage Reasons that match the OData filter criteria.

## Users

- `GET /api/Users` — Gets the Users that match the OData filter criteria.
- `GET /api/Users/{UserID}` — Gets the User. (params: UserID)
- `GET /api/Users/{UserID}/Roles` — Gets the User's Roles. (params: UserID)

## VariationActivities

- `GET /api/VariationActivities` — Gets the Variation Activities that match the OData filter criteria.

## Variations

- `GET /api/Variations/Approvals` — Gets the Variation Approvals that match the OData filter criteria.
- `GET /api/Variations/Documents` — Gets the Variation Documents that match the OData filter criteria.
- `GET /api/Variations/Reasons` — Gets the Variation Reasons that match the OData filter criteria.
- **[WRITE]** `DELETE /api/Variations/{VariationID}` — Deletes the Variation. (params: VariationID)
- **[WRITE]** `PATCH /api/Variations/{VariationID}` — Updates the Variation. (params: VariationID) (json body)

## Version

- `GET /api/versions` — Gets the list of available API interface versions supported by the API.

## WorkReleases

- `GET /api/WorkReleases/Documents` — Gets the Work Release Documents that match the OData filter criteria.

## Core schema fields

Property names for the entities queries touch most (use with
`$select` / `$filter` / `$orderby`). Full schemas: widen
`CORE_SCHEMA_KEYWORDS` in the generator and re-run.

Collection GETs wrap results in a paging envelope:
`currentPage, pagedItems, sourceCollectionCount` (or OData
`@odata.context, @odata.count, value`).

- **AddWorkflowTemplateToJobCommand**: insertBeforeActivityID, shouldLinkPredecessors, shouldLinkSuccessors, workflowTemplateID
- **AlertDocumentViewModel**: alertID, createdBy, createdOn, description, documentID, documentType, documentTypeID, extension, version
- **AlertRecipientViewModel**: acknowledged, acknowledgedOnUtc, read, readOnUtc
- **AlertRecipientViewModel**: userID, userName
- **AlertViewModel**: alertID, body, createdBy, createdByUserID, createdOnUtc, hasBeenAcknowledged, hasBeenRead, notifyEveryone, parentAlertID, subject
- **AttachableDocumentTypeViewModel**: documentTypeID, name, parentDocumentTypeID
- **AutoAssignDefectsServiceProviderViewModel**: defectID, serviceProviderID
- **BookDefectsStartCommand**: bookedStartDate
- **BookJobActivitysStartCommand**: bookedStartDate
- **ClientLogEntry**: context, exception, level, message, timestampUtc
- **ClientViewModel**: abn, abnLastUpdatedOnUtc, clientID, contactIDsLastUpdatedOnUtc, createdBy, createdOnUtc, entityCode, entityCodeLastUpdatedOnUtc, name, nameLastUpdatedOnUtc, postalAddress, salespersonID, salespersonLastUpdatedOnUtc, workAddress, workContactDetails, workUrl, workUrlLastUpdatedOnUtc
- **ClientWorkflowActivityViewModel**: activityID, actualCompletionDate, actualStartDate, bookedCompletionDate, bookedStartDate, description, forecastedCompletionDate, forecastedStartDate, hasAlerts, hasMessages, sequence, serviceProvider, serviceProviderID, serviceType, serviceTypeID, user, userID
- **ClientWorkflowContactViewModel**: clientContactType, contactDescriptor, contactID, containerID, displayName
- **ClientWorkflowDocumentViewModel**: attachedOn, description, documentID, documentType, extension, version
- **ClientWorkflowViewModel**: clientName, createdBy, createdOn, name, siteAddress, workflowID, workflowStatus, workflowStatusLastUpdatedBy, workflowStatusLastUpdatedOn
- **ClientWorkflowViewModel**: clientName, name, siteAddress, workflowID, workflowStatus
- **CompleteDefectCommand**: completionDate
- **CompleteDefectViewModel**: completionDate, defectID
- **CompleteInspectionCommand**: completedSignOffBuilderSignature, completedSignOffClientSignature
- **CompleteJobActivityCommand**: completionDate
- **CompleteJobActivityViewModel**: activityID, completionDate, createdInspectionID
- **ContactDetailsPrimaryCommunicationMethodViewModel**: contactDetailsPrimaryCommunicationMethodID, description
- **ContactInformationViewModel**: direct, email, mobile, phone, preferredContactMethod
- **CreateClientCommand**: abn, entityCode, name, postalAddress, salespersonID, workAddress, workContactDetails, workUrl
- **CreateClientContactCommand**: isPrimaryContact, isSecondaryContact, preferredCommunicationGroupID, relationship
- **CreateClientContactViewModel**: clientID, personID
- **CreateClientLogsCommand**: entries, source
- **CreateDefectCommand**: action, defectCategoryID, description, locationIDs, serviceProviderID, serviceTypeID, summary, userID
- **CreateDocumentDto**: description, file
- **CreateInspectionFromTemplateCommand**: inspectionTemplateID
- **CreateJobCommand**: clientID, contractNumber, contractValueExcludingGst, contractValueIncludingGst, customFieldValues, regionID, siteAddress, startDate, workflowTemplateID
- **CreateJobContactCommand**: preferredCommunicationGroupID, relationship
- **CreateJobContactViewModel**: jobID, personID
- **CreateMessageReplyCommand**: replyBody
- **CreatePersonalContactDetailsDto**: contactDetailsPrimaryCommunicationMethodID, email, fax, mobile, phone
- **CreateServiceProviderContactCommand**: isAccountsContact, isDefectWorkReleaseContact, isJobActivityWorkReleaseContact, isOrdersContact, isPrimaryContact, isWhsContact, relationship
- **CreateServiceProviderContactViewModel**: personID, serviceProviderID
- **CreateSubJobCommand**: subJobRelationshipID, workflowTemplateID
- **CreateVariationCommand**: costExcludingGst, description, markUpPercentage, reference, startDate, summary, variationApprovalID, variationReasonID
- **CreateWorkContactDetailsDto**: contactDetailsPrimaryCommunicationMethodID, direct, email, fax, mobile, phone
- **CreatedAlertViewModel**: alertID, createdBy, createdOnUtc, documents
- **CreatedDefectViewModel**: createdBy, createdOnUtc, defectID, sequence
- **CreatedDocumentViewModel**: createdBy, createdOnUtc, documentID, documentTypeID
- **CreatedMessageViewModel**: createdBy, createdOnUtc, documents, messageID
- **DefaultDefectCategoriesViewModel**: defaultFromActivityDefectCategoryID, defaultNewDefectCategoryID
- **DefectAlertViewModel**: alertID, body, createdBy, createdByUserID, createdOnUtc, defectID, hasBeenAcknowledged, hasBeenRead, notifyEveryone, parentAlertID, subject
- **DefectCategoryViewModel**: defectCategoryID, isActive, name
- **DefectViewModel**: action, actualCompletionDate, actualStartDate, backChargeAmount, backChargeServiceProvider, backChargeServiceProviderID, bookedCompletionDate, bookedStartDate, defectCategoryID, defectID, description, duration, forecastedCompletionDate, forecastedStartDate, hasAlerts, hasMessages, isBackChargeRequired, jobID, locationIDs, notApplicableDate, sequence, serviceProvider, serviceProviderID, serviceType, serviceTypeID, summary, user, userID
- **DocumentMetadataViewModel**: currentVersionCreatedBy, currentVersionCreatedOnUtc, description, documentID, documentType, documentTypeID, extension, note, versionNumber
- **DocumentTypeViewModel**: documentTypeID, name, parentDocumentTypeID
- **DocumentTypesViewModel**: documentTypes
- **DocumentViewModel**: attachedOnUtc, description, documentID, documentType, documentTypeID, extension, fileCreatedOnUtc, version
- **DocumentViewModel**: documentID
- **GetClientContactsViewModel**: createdBy, createdOnUtc, clientID, email, fullName, isPrimaryContact, isPrimaryContactLastUpdatedOnUtc, isSecondaryContact, isSecondaryContactLastUpdatedOnUtc, mobile, personID, phone, relationship, relationshipLastUpdatedOnUtc, workDirect
- **GetDefectAttachableDocumentsAndOrdersViewModel**: documents, orders
- **GetDefectWorkReleaseEmailTemplateViewModel**: attachments, bccRecipients, ccRecipients, emailTemplateID, htmlBody, subject, toRecipients
- **GetDefectsAssignableServiceProvidersViewModel**: abn, complianceState, fax, isActive, legalName, phone, serviceProviderID, tradingAsName
- **GetInspectionLocationViewModel**: activeQuestions, answeredQuestions, locationID, name, progressPercent, sequence, totalQuestions
- **GetInspectionsViewModel**: activeQuestions, answeredQuestions, completedByUser, completedOnUtc, completedSignOffName, completedSignOffSignature, createdBy, createdOnUtc, defectCategory, inspectionDefects, inspectionID, isReadOnly, jobID, locations, name, progressPercent, totalQuestions
- **GetJobActivityAttachableDocumentsAndOrdersViewModel**: documents, orders
- **GetJobActivityWorkReleaseEmailTemplateViewModel**: attachments, bccRecipients, ccRecipients, emailTemplateID, htmlBody, subject, toRecipients
- **GetJobActivitysAssignableServiceProvidersViewModel**: abn, complianceState, fax, isActive, legalName, phone, serviceProviderID, tradingAsName
- **GetJobContactsViewModel**: createdBy, createdOnUtc, email, fullName, jobID, mobile, personID, phone, preferredCommunicationGroup, preferredCommunicationGroupLastUpdatedOnUtc, relationship, relationshipLastUpdatedOnUtc, workDirect
- **GetJobCustomFieldValuesViewModel**: customFieldID, date, jobID, number, text, valueLastUpdatedOnUtc
- **GetJobWorkflowStatusesViewModel**: workflowStatusID, isActive, isActiveWorkflow, name, sequence
- **GetJobsDocumentTypesViewModel**: documentTypeID, isInUse, name, parentDocumentTypeID
- **GetJobsQuery**: shouldShowMyJobsOnly, workflowStatusIDs
- **GetJobsViewModel**: clientID, clientLastUpdatedOnUtc, clientName, clientNameLastUpdatedOnUtc, contract, contractEndDate, contractEndDateLastUpdatedOnUtc, contractNumber, contractNumberLastUpdatedOnUtc, contractStartDate, contractStartDateLastUpdatedOnUtc, contractValueExcludingGst, contractValueExcludingGstLastUpdatedOnUtc, contractValueIncludingGst, contractValueIncludingGstLastUpdatedOnUtc, createdBy, createdOnUtc, customFieldValues, jobID, region, regionLastUpdatedOnUtc, siteAddress, startDate, startDateLastUpdatedOnUtc, workflowStatusID, workflowStatusLastUpdatedOnUtc, workflowStatusName
- **GetJobsViewModel.ContractComparisonOptionsViewModel**: shouldContractUseActivityCompletionDate, useContractComparison, useContractCompletionTriggerActivityID
- **GetJobsViewModel.ContractDurationOptionsViewModel**: contractDuration, contractExtensionOfTimeAllowanceDays, useContractDuration
- **GetJobsViewModel.ContractEndOptionsViewModel**: contractEndsOnDate, useContractEnd
- **GetJobsViewModel.ContractStartOptionsViewModel**: contractStartOffset, contractStartsOnDate, contractStartTriggerActivityIDs, isContractStartOffset, shouldContractStartDateUseTriggerActivities, useContractStart
- **GetJobsViewModel.ContractViewModel**: contractCalculationID, contractComparisonOptions, contractDurationOptions, contractEndOptions, contractStartOptions
- **GetLiinkDocumentTypesResponse**: inductionDocumentTypeID, serviceProviderComplianceDocumentTypeID, siteSpecificRiskAssessmentDocumentTypeID
- **GetVariationApprovalsViewModel**: description, isAccepted, isActive, isActiveWorkflow, isDefault, variationApprovalID
- **GetVariationDocumentViewModel**: createdBy, createdOnUtc, description, documentID, documentType, documentTypeID, extension, variationID, version
- **GetVariationReasonsViewModel**: description, isActive, isDefault, variationReasonID
- **GetWorkReleaseDocumentViewModel**: createdBy, createdOnUtc, description, documentID, documentType, documentTypeID, extension, workReleaseID, version
- **InspectionAnswerRequirementViewModel**: name, inspectionAnswerRequirementID
- **InspectionAnswerStateViewModel**: name, inspectionAnswerStateID
- **InspectionAnswerViewModel**: action, answerDocuments, answerState, availableServiceTypes, createsDefect, detail, inspectionAnswerID, isActive, question, questionDocuments, requiresDetails, requiresPhoto, selectedServiceTypes
- **InspectionCompletionDefectViewModel**: action, assignedUser, description, detail, locations, serviceType
- **InspectionDefectViewModel**: action, description, detail, documents, inspectionDefectID, locations, sequence, serviceType
- **InspectionLocationViewModel**: answers, inspectionLocationID, locationID, name, sequence
- **InspectionTemplateViewModel**: defectCategoryName, inspectionTemplateID, name
- **InspectionValidationErrorsViewModel**: detail, errors, status, title, type
- **InspectionViewModel**: answerIDs, builderName, builderSignature, clientName, clientSignature, completedByUser, completedByUserID, completedOnUtc, createdBy, createdByUserID, createdOnUtc, defaultAnswerStateID, defaultReportIncludedAnswerIDs, defectCategory, defectCategoryID, defectIDs, inspectionID, jobID, locations, name, reportTemplateID, shouldAutoGenerateReportOnCompletion
- **JobActivityAlertViewModel**: alertID, body, createdBy, createdByUserID, createdOnUtc, hasBeenAcknowledged, hasBeenRead, jobActivityID, notifyEveryone, parentAlertID, subject
- **JobActivityCompletionAnswerStateViewModel**: completionAnswerStateID, description
- **JobActivityCompletionAnswerViewModel**: answerState, answerStateID, note
- **JobActivityCompletionQuestionViewModel**: answer, completionQuestionID, questionText, sequence
- **JobActivityViewModel**: bookedCompletionDate, bookedCompletionDateLastUpdatedOnUtc, bookedStartDate, bookedStartDateLastUpdatedOnUtc, completionDate, completionDateLastUpdatedOnUtc, createdBy, createdOnUtc, description, forecastedCompletionDate, forecastedCompletionDateLastUpdatedOnUtc, forecastedStartDate, forecastedStartDateLastUpdatedOnUtc, hasAlerts, hasCompletionQuestions, hasMessages, isNotApplicable, isNotApplicableLastUpdatedOnUtc, jobActivityID, jobID, sequence, sequenceLastUpdatedOnUtc, serviceDescription, serviceID, serviceProvider, serviceProviderID, serviceProviderLastUpdatedOnUtc, serviceType, serviceTypeID, startDate, startDateLastUpdatedOnUtc, user, userID, userLastUpdatedOnUtc
- **JobAlertViewModel**: alertID, body, createdBy, createdByUserID, createdOnUtc, hasBeenAcknowledged, hasBeenRead, jobID, notifyEveryone, parentAlertID, subject
- **JobContactViewModel**: contactID, contactDescriptor, containerID, displayName, jobContactType
- **JobDocumentViewModel**: attachedOnUtc, description, documentID, documentTypeID, extension, fileCreatedOnUtc, jobID, version
- **JobInspectionViewModel**: clientName, completedBy, completedOnUtc, contractNumber, createdBy, createdOnUtc, defectCategory, inspectionID, jobID, name, progressPercent, siteAddress
- **JobVariationViewModel**: costExcludingGst, costExcludingGstLastUpdatedOnUtc, createdBy, createdOnUtc, description, descriptionLastUpdatedOnUtc, gst, gstLastUpdatedOnUtc, markupPercentage, markUpPercentageLastUpdatedOnUtc, reference, referenceLastUpdatedOnUtc, startDate, startDateLastUpdatedOnUtc, summary, summaryLastUpdatedOnUtc, variationApprovalID, variationApprovalLastUpdatedOnUtc, variationID, variationNumber, variationNumberLastUpdatedOnUtc, variationReasonID, variationReasonLastUpdatedOnUtc
- **JobViewModel**: clientName, contractNo, jobID, siteAddress, workflowStatus
- **JobViewModel**: jobID
- **JobWorkflowTemplateViewModel**: name, workflowTemplateID
- **JobWorkflowTemplatesViewModel**: jobWorkflowTemplates
- **LocationDto**: isActive, locationID, name, sequence
- **LocationViewModel**: isActive, locationID, name
- **LocationViewModel**: locationID, name
- **MessageDocumentViewModel**: createdBy, createdOn, description, documentID, documentType, documentTypeID, extension, messageID, version
- **MessageReplyViewModel**: alertRecipients, messageID, messageType, subject
- **MessageViewModel**: acknowledgedByRecipients, acknowledgedByRequester, createdOnUtc, fromUserID, fromUserName, messageID, openedByRecipients, openedByRequester, parentMessage, parentMessageID, subject, text, type
- **MessageViewModel**: body, createdBy, createdOnUtc, messageID, messageType, subject
- **MobileAppDocumentViewModel**: attachedOn, description, documentID, documentType, extension, version
- **NAJobActivityCommand**: shouldNotNALinkedActivities
- **NotApplicableDefectViewModel**: notApplicableDate
- **NotApplicableJobActivityViewModel**: notApplicableDate
- **PersonalContactDetailsViewModel**: email, emailLastUpdatedOnUtc, fax, faxLastUpdatedOnUtc, mobile, mobileLastUpdatedOnUtc, phone, phoneLastUpdatedOnUtc, primaryCommunicationMethod, primaryCommunicationMethodLastUpdatedOnUtc
- **PutAlertRecipientCommand**: acknowledged, read
- **PutJobActivityCompletionAnswerCommand**: completionAnswerStateID, note
- **ServiceProviderContactViewModel**: createdBy, createdOnUtc, fullName, fullNameLastUpdatedOnUtc, isAccountsContact, isAccountsContactLastUpdatedOnUtc, isDefectWorkReleaseContact, isDefectWorkReleaseContactLastUpdatedOnUtc, isJobActivityWorkReleaseContact, isJobActivityWorkReleaseContactLastUpdatedOnUtc, isOrdersContact, isOrdersContactLastUpdatedOnUtc, isPrimaryContact, isPrimaryContactLastUpdatedOnUtc, isWhsContact, isWhsContactLastUpdatedOnUtc, personID, relationship, relationshipLastUpdatedOnUtc, serviceProviderID, workContactDetails, workReleaseRegionsLastUpdatedOnUtc, workReleaseServiceTypesLastUpdatedOnUtc
- **SetDefectBookedStartConfirmationCommand**: confirmedByOverride, isConfirming
- **SetJobActivityBookedStartConfirmationCommand**: confirmedByOverride, isConfirming
- **SubJobRelationshipViewModel**: description, isActive, subJobRelationshipID
- **UpdateClientCommand**: abn, entityCode, name, postalAddress, salespersonID, workAddress, workContactDetails, workUrl
- **UpdateClientContactCommand**: isPrimaryContact, isSecondaryContact, preferredCommunicationGroupID, relationship
- **UpdateDefectCommand**: serviceProviderID, shouldUpdateOrders, startDate
- **UpdateInspectionAnswerViewModel**: activeInspectionAnswerIDs, inactiveInspectionAnswerIDs
- **UpdateJobActivityCommand**: serviceProviderID, startDate, shouldUpdateOrders
- **UpdateJobCommand**: contractNumber, contractValueExcludingGst, contractValueIncludingGst, customFieldValues, regionID, siteAddress, startDate
- **UpdateJobContactCommand**: preferredCommunicationGroupID, relationship
- **UpdateJobsContractCommand**: contractCalculationID, contractComparisonOptions, contractDurationOptions, contractEndOptions, contractStartOptions
- **UpdateJobsContractCommand.UpdateContractComparisonOptionsDto**: shouldContractUseActivityCompletionDate, useContractComparison, useContractCompletionTriggerActivityID
- **UpdateJobsContractCommand.UpdateContractDurationOptionsDto**: contractDuration, contractExtensionOfTimeAllowanceDays, useContractDuration
- **UpdateJobsContractCommand.UpdateContractEndOptionsDto**: contractEndsOnDate, useContractEnd
- **UpdateJobsContractCommand.UpdateContractStartOptionsDto**: contractStartOffset, contractStartsOnDate, contractStartTriggerActivityIDsToAdd, contractStartTriggerActivityIDsToRemove, isContractStartOffset, useContractStart
- **UpdatePersonalContactDetailsDto**: contactDetailsPrimaryCommunicationMethodID, email, fax, mobile, phone
- **UpdateServiceProviderContactCommand**: isAccountsContact, isDefectWorkReleaseContact, isJobActivityWorkReleaseContact, isOrdersContact, isPrimaryContact, isWhsContact, relationship
- **UpdateVariationCommand**: costExcludingGst, description, markUpPercentage, reference, startDate, summary, variationApprovalID, variationReasonID
- **UpdateWorkContactDetailsDto**: contactDetailsPrimaryCommunicationMethodID, direct, email, fax, mobile, phone
- **VariationActivityViewModel**: bookedCompletionDate, bookedStartDate, completionDate, description, forecastedCompletionDate, forecastedStartDate, hasAlerts, hasCompletionQuestions, hasMessages, isNotApplicable, sequence, serviceDescription, serviceID, serviceProvider, serviceProviderID, serviceType, serviceTypeID, startDate, user, userID, variationActivityID, variationID
- **WorkContactDetailsViewModel**: direct, directLastUpdatedOnUtc, email, emailLastUpdatedOnUtc, fax, faxLastUpdatedOnUtc, mobile, mobileLastUpdatedOnUtc, phone, phoneLastUpdatedOnUtc, primaryCommunicationMethod, primaryCommunicationMethodLastUpdatedOnUtc
- **WorkReleaseContactViewModel**: direct, email, fax, fullName, mobile, phone, primaryCommunicationMethod
