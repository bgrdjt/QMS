' ============================================================
' QMS Word Ribbon v1.1 — Routing & Notification Support
' ============================================================

Option Explicit

Private Const API_BASE As String = "http://127.0.0.1:5151"

' ── HELPERS ──────────────────────────────────────────────────────────────────

Private Function APIGet(endpoint As String) As String
    On Error GoTo Err
    Dim h As Object: Set h = CreateObject("MSXML2.XMLHTTP.6.0")
    h.Open "GET", API_BASE & endpoint, False: h.send
    APIGet = h.responseText: Exit Function
Err: APIGet = "{""error"":""offline""}"
End Function

Private Function APIPost(endpoint As String, body As String) As String
    On Error GoTo Err
    Dim h As Object: Set h = CreateObject("MSXML2.XMLHTTP.6.0")
    h.Open "POST", API_BASE & endpoint, False
    h.setRequestHeader "Content-Type", "application/json"
    h.send body: APIPost = h.responseText: Exit Function
Err: APIPost = "{""error"":""offline""}"
End Function

Private Function JV(json As String, key As String) As String
    ' Extract a value from flat JSON by key
    Dim p As Long, e As Long
    p = InStr(json, """" & key & """:")
    If p = 0 Then JV = "": Exit Function
    p = p + Len(key) + 3
    Do While Mid(json, p, 1) = " ": p = p + 1: Loop
    If Mid(json, p, 1) = """" Then
        p = p + 1: e = InStr(p, json, """")
        JV = Mid(json, p, e - p)
    Else
        e = p
        Do While Mid(json, e, 1) <> "," And Mid(json, e, 1) <> "}" And e < Len(json)
            e = e + 1
        Loop
        JV = Trim(Mid(json, p, e - p))
    End If
End Function

Private Function ServerRunning() As Boolean
    On Error GoTo No
    Dim h As Object: Set h = CreateObject("MSXML2.XMLHTTP.6.0")
    h.Open "GET", API_BASE & "/ping", False: h.send
    ServerRunning = (h.Status = 200): Exit Function
No: ServerRunning = False
End Function

Private Function CheckServer() As Boolean
    If Not ServerRunning() Then
        MsgBox "QMS Server is not running." & vbCrLf & _
               "Please launch the QMS Desktop App first.", _
               vbExclamation, "QMS Offline"
        CheckServer = False
    Else
        CheckServer = True
    End If
End Function

Private Function GetDocID() As String
    On Error Resume Next
    If ActiveDocument Is Nothing Then GetDocID = "": Exit Function
    Dim rx As Object: Set rx = CreateObject("VBScript.RegExp")
    rx.Pattern = "([A-Z]{2,4}-\d{3})"
    Dim m As Object: Set m = rx.Execute(ActiveDocument.Name)
    If m.Count > 0 Then GetDocID = m(0).Value Else GetDocID = ""
    On Error GoTo 0
End Function

Private Function GetCurrentUser() As String
    Dim cfg As String: cfg = APIGet("/config")
    Dim u As String: u = JV(cfg, "current_user")
    If u = "" Then u = Environ("USERNAME")
    GetCurrentUser = u
End Function

Private Function GetCurrentEmail() As String
    Dim cfg As String: cfg = APIGet("/config")
    GetCurrentEmail = JV(cfg, "current_email")
End Function

' ── STATUS ───────────────────────────────────────────────────────────────────

Public Sub QMS_ShowStatus(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbInformation, "QMS": Exit Sub
    End If
    Dim resp As String: resp = APIGet("/documents/" & docID)
    If InStr(resp, """error""") > 0 Then
        MsgBox "Document not found in register.", vbExclamation, "QMS": Exit Sub
    End If
    ' Routing info
    Dim qresp As String: qresp = APIGet("/routing/queue?doc_id=" & docID & "&status=PENDING")
    Dim routeInfo As String
    If InStr(qresp, "route_id") > 0 Then
        routeInfo = vbCrLf & "⚡ Active routing: IN PROGRESS"
    Else
        routeInfo = vbCrLf & "No active routing"
    End If
    MsgBox docID & "  Rev " & JV(resp, "version") & vbCrLf & _
           "Title:  " & JV(resp, "title") & vbCrLf & _
           "Status: " & JV(resp, "status") & vbCrLf & _
           "Owner:  " & JV(resp, "owner") & vbCrLf & _
           IIf(JV(resp, "approved_by") <> "", "Approved by: " & JV(resp, "approved_by") & _
               " on " & JV(resp, "approved_date") & vbCrLf, "") & _
           IIf(JV(resp, "next_review_date") <> "", "Next Review: " & JV(resp, "next_review_date") & vbCrLf, "") & _
           routeInfo, vbInformation, "QMS Status — " & docID
End Sub

' ── ROUTING: SUBMIT FOR REVIEW ───────────────────────────────────────────────

Public Sub QMS_RouteForReview(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    ' Check status
    Dim resp As String: resp = APIGet("/documents/" & docID)
    Dim status As String: status = JV(resp, "status")
    If status <> "DRAFT" And status <> "IN_REVIEW" Then
        MsgBox "Only DRAFT or IN_REVIEW documents can be routed for review." & vbCrLf & _
               "Current status: " & status, vbExclamation, "QMS": Exit Sub
    End If
    ' Get roster
    Dim rosterResp As String: rosterResp = APIGet("/roster")
    If InStr(rosterResp, "name") = 0 Then
        MsgBox "No team members configured." & vbCrLf & _
               "Please add reviewers in the QMS Desktop App → Team Roster.", _
               vbExclamation, "QMS": Exit Sub
    End If
    ' Save first
    If Not ActiveDocument.Saved Then ActiveDocument.Save
    ' Get reviewer name input (simplified — full picker is in the desktop app)
    Dim reviewer As String
    reviewer = InputBox("Enter reviewer name(s) — comma separated:" & vbCrLf & _
                        "(For multi-select, use QMS Desktop App → Documents → Route for Review)", _
                        "QMS — Route for Review", "")
    If reviewer = "" Then Exit Sub
    Dim notes As String
    notes = InputBox("Notes for the reviewer (optional):", "QMS — Review Notes", "")
    Dim dueDays As String
    dueDays = InputBox("Due in how many days?", "QMS — Due Date", "7")
    If Not IsNumeric(dueDays) Then dueDays = "7"
    ' Build reviewer list from comma-separated names
    Dim names() As String: names = Split(reviewer, ",")
    Dim reviewerJSON As String: reviewerJSON = "["
    Dim i As Integer
    For i = 0 To UBound(names)
        Dim nm As String: nm = Trim(names(i))
        If nm <> "" Then
            If Len(reviewerJSON) > 1 Then reviewerJSON = reviewerJSON & ","
            reviewerJSON = reviewerJSON & "{""name"":""" & nm & """,""email"":""""}"
        End If
    Next i
    reviewerJSON = reviewerJSON & "]"
    Dim body As String
    body = "{""doc_id"":""" & docID & """," & _
           """reviewers"":" & reviewerJSON & "," & _
           """sender_name"":""" & GetCurrentUser() & """," & _
           """sender_email"":""" & GetCurrentEmail() & """," & _
           """notes"":""" & Replace(notes, """", "'") & """," & _
           """due_days"":" & CInt(dueDays) & "}"
    Dim result As String: result = APIPost("/routing/submit-review", body)
    If JV(result, "ok") = "true" Then
        Dim rcount As String: rcount = JV(result, "routes_created")
        MsgBox docID & " has been routed for review." & vbCrLf & _
               rcount & " reviewer(s) notified." & vbCrLf & vbCrLf & _
               "The document status is now IN_REVIEW." & vbCrLf & _
               "Reviewers will see it in the QMS App → Routing panel.", _
               vbInformation, "QMS — Routed for Review"
    Else
        MsgBox "Error: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' ── ROUTING: SUBMIT FOR APPROVAL ─────────────────────────────────────────────

Public Sub QMS_RouteForApproval(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    Dim resp As String: resp = APIGet("/documents/" & docID)
    If JV(resp, "status") <> "IN_REVIEW" Then
        MsgBox "Only IN_REVIEW documents can be routed for approval." & vbCrLf & _
               "Current status: " & JV(resp, "status"), vbExclamation, "QMS": Exit Sub
    End If
    If Not ActiveDocument.Saved Then ActiveDocument.Save
    ' Try to get default approver
    Dim prefix As String: prefix = Left(docID, InStr(docID, "-") - 1)
    Dim defResp As String: defResp = APIGet("/roster/defaults?doc_type=" & prefix)
    Dim approverName As String: approverName = JV(defResp, "name")
    Dim approverEmail As String: approverEmail = JV(defResp, "email")
    approverName = InputBox("Approver name:", "QMS — Route for Approval",
                             IIf(approverName <> "", approverName, ""))
    If approverName = "" Then Exit Sub
    approverEmail = InputBox("Approver email:", "QMS — Approver Email",
                              IIf(approverEmail <> "", approverEmail, ""))
    Dim notes As String
    notes = InputBox("Notes for the approver (optional):", "QMS — Approval Notes", "")
    Dim body As String
    body = "{""doc_id"":""" & docID & """," & _
           """approver"":{""name"":""" & approverName & """,""email"":""" & approverEmail & """}," & _
           """sender_name"":""" & GetCurrentUser() & """," & _
           """notes"":""" & Replace(notes, """", "'") & """}"
    Dim result As String: result = APIPost("/routing/submit-approval", body)
    If JV(result, "ok") = "true" Then
        MsgBox docID & " has been sent to " & approverName & " for approval." & vbCrLf & vbCrLf & _
               "The approver will see it in QMS App → Routing panel.", _
               vbInformation, "QMS — Routed for Approval"
    Else
        MsgBox "Error: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' ── ROUTING: COMPLETE REVIEW ─────────────────────────────────────────────────

Public Sub QMS_CompleteReview(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    ' Find pending review route for this doc assigned to current user
    Dim qresp As String
    qresp = APIGet("/routing/queue?doc_id=" & docID & "&status=PENDING")
    If InStr(qresp, "route_id") = 0 Then
        MsgBox "No pending review found for " & docID & "." & vbCrLf & _
               "Check QMS Desktop App → Routing for your assigned items.", _
               vbInformation, "QMS": Exit Sub
    End If
    ' Extract first route_id (simplified — full list in desktop app)
    Dim routeID As String: routeID = JV(qresp, "route_id")
    If routeID = "" Then
        MsgBox "Could not identify route. Use QMS Desktop App → Routing to complete.", _
               vbInformation, "QMS": Exit Sub
    End If
    Dim notes As String
    notes = InputBox("Review notes / summary of findings:" & vbCrLf & _
                     "(Describe changes required or confirm document is ready for approval)", _
                     "QMS — Complete Review", "")
    Dim rejected As Boolean: rejected = False
    Dim choice As Integer
    choice = MsgBox("Did this document PASS review?" & vbCrLf & vbCrLf & _
                    "Yes = Reviewed, ready for approval" & vbCrLf & _
                    "No  = Return to author for revision", _
                    vbYesNo + vbQuestion, "QMS — Review Outcome")
    If choice = vbNo Then rejected = True
    If Not ActiveDocument.Saved Then ActiveDocument.Save
    Dim body As String
    body = "{""route_id"":""" & routeID & """," & _
           """doc_id"":""" & docID & """," & _
           """reviewer_name"":""" & GetCurrentUser() & """," & _
           """notes"":""" & Replace(notes, """", "'") & """," & _
           """rejected"":" & LCase(CStr(rejected)) & "}"
    Dim result As String: result = APIPost("/routing/complete-review", body)
    If JV(result, "ok") = "true" Then
        If rejected Then
            MsgBox "Review submitted — document returned to author." & vbCrLf & _
                   "Author will be notified to address your comments.", _
                   vbInformation, "QMS — Review Complete"
        Else
            MsgBox "Review complete — document is ready for approval routing." & vbCrLf & _
                   "Author will be notified.", vbInformation, "QMS — Review Complete"
        End If
    Else
        MsgBox "Error: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' ── RECALL ───────────────────────────────────────────────────────────────────

Public Sub QMS_RecallDocument(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    Dim qresp As String
    qresp = APIGet("/routing/queue?doc_id=" & docID & "&status=PENDING")
    If InStr(qresp, "route_id") = 0 Then
        MsgBox "No active routing found for " & docID & ".", vbInformation, "QMS": Exit Sub
    End If
    Dim routeID As String: routeID = JV(qresp, "route_id")
    If MsgBox("Recall " & docID & " from review?" & vbCrLf & _
              "This will cancel the current routing and return the document to Draft.",  _
              vbYesNo + vbQuestion, "QMS — Recall") = vbNo Then Exit Sub
    Dim body As String
    body = "{""route_id"":""" & routeID & """," & _
           """doc_id"":""" & docID & """," & _
           """user"":""" & GetCurrentUser() & """}"
    Dim result As String: result = APIPost("/routing/recall", body)
    If JV(result, "ok") = "true" Then
        MsgBox docID & " has been recalled." & vbCrLf & _
               "Reviewers have been notified.", vbInformation, "QMS — Recalled"
    Else
        MsgBox "Error: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' ── APPROVE ──────────────────────────────────────────────────────────────────

Public Sub QMS_ApproveDocument(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    Dim resp As String: resp = APIGet("/documents/" & docID)
    If JV(resp, "status") <> "IN_REVIEW" Then
        MsgBox "Only IN_REVIEW documents can be approved." & vbCrLf & _
               "Current status: " & JV(resp, "status"), vbExclamation, "QMS": Exit Sub
    End If
    If Not ActiveDocument.Saved Then ActiveDocument.Save
    Dim approver As String: approver = GetCurrentUser()
    If MsgBox("Approve " & docID & "?" & vbCrLf & vbCrLf & _
              "Approver: " & approver & vbCrLf & _
              "This generates a stamped PDF and closes the document.", _
              vbYesNo + vbCritical, "QMS — Confirm Approval") = vbNo Then Exit Sub
    Dim body As String
    body = "{""to"":""approved"",""user"":""" & approver & """}"
    Dim result As String: result = APIPost("/documents/" & docID & "/promote", body)
    If JV(result, "ok") = "true" Then
        MsgBox docID & " Rev" & JV(result, "version") & " APPROVED." & vbCrLf & _
               "Stamped PDF generated. Team notified.", vbInformation, "QMS — Approved"
        ActiveDocument.Close SaveChanges:=False
    Else
        MsgBox "Error: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' ── REDLINE ──────────────────────────────────────────────────────────────────

Public Sub QMS_StartRedline(control As IRibbonControl)
    ActiveDocument.TrackRevisions = True
    Dim docID As String: docID = GetDocID()
    Dim reviewer As String: reviewer = GetCurrentUser()
    Dim rng As Range: Set rng = ActiveDocument.Range(0, 0)
    ActiveDocument.Comments.Add Range:=rng, _
        Text:="REDLINE REVIEW — Reviewer: " & reviewer & " — " & Format(Now, "yyyy-mm-dd HH:MM")
    MsgBox "Track Changes ON. Review comment added." & vbCrLf & vbCrLf & _
           "Make your comments, then click 'Complete Review' when done.", _
           vbInformation, "QMS — Redline Active"
End Sub

' ── NOTIFICATIONS ────────────────────────────────────────────────────────────

Public Sub QMS_ShowNotifications(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim cfg As String: cfg = APIGet("/config")
    Dim user As String: user = JV(cfg, "current_user")
    Dim email As String: email = JV(cfg, "current_email")
    Dim resp As String
    resp = APIGet("/notifications?user=" & user & "&email=" & email)
    If InStr(resp, "notif_id") = 0 Then
        MsgBox "No notifications.", vbInformation, "QMS — Notifications": Exit Sub
    End If
    ' Count unread
    Dim unread As Integer: unread = 0
    Dim pos As Long: pos = 1
    Do
        pos = InStr(pos, resp, """dismissed"": false")
        If pos = 0 Then Exit Do
        unread = unread + 1: pos = pos + 10
    Loop
    MsgBox "You have " & unread & " unread notification(s)." & vbCrLf & vbCrLf & _
           "Open the QMS Desktop App → Notifications for full detail,  " & vbCrLf & _
           "or click 'Open QMS App' in the ribbon.", _
           vbInformation, "QMS — Notifications (" & unread & " unread)"
End Sub

' ── AUDIT LOG FOR THIS DOC ───────────────────────────────────────────────────

Public Sub QMS_ShowAuditLog(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then Exit Sub
    Dim resp As String: resp = APIGet("/audit-log")
    Dim out As String: out = "Audit log for " & docID & ":" & vbCrLf & vbCrLf
    Dim pos As Long: pos = 1: Dim count As Integer: count = 0
    Do
        pos = InStr(pos, resp, """doc_id"": """ & docID & """")
        If pos = 0 Then Exit Do
        Dim os As Long: os = InStrRev(resp, "{", pos)
        Dim oe As Long: oe = InStr(pos, resp, "}")
        If os > 0 And oe > 0 Then
            Dim blk As String: blk = Mid(resp, os, oe - os + 1)
            count = count + 1
            out = out & count & ". " & Left(JV(blk, "timestamp"), 16) & _
                  "  " & JV(blk, "action") & "  —  " & JV(blk, "user") & vbCrLf
        End If
        pos = oe + 1
    Loop
    If count = 0 Then out = out & "(No entries found)"
    MsgBox out, vbInformation, "QMS — Audit: " & docID
End Sub

' ── RELATED DOCS ─────────────────────────────────────────────────────────────

Public Sub QMS_ViewRelated(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then Exit Sub
    Dim resp As String: resp = APIGet("/documents/" & docID)
    Dim rel As String: rel = JV(resp, "related_docs")
    If rel = "" Then rel = "None specified"
    MsgBox "Related documents for " & docID & ":" & vbCrLf & vbCrLf & rel, _
           vbInformation, "QMS — Related Documents"
End Sub

' ── OPEN QMS APP ─────────────────────────────────────────────────────────────

Public Sub QMS_OpenApp(control As IRibbonControl)
    Dim p As String: p = Environ("QMS_APP_PATH")
    If p = "" Then
        MsgBox "QMS_APP_PATH not set. Launch the QMS App manually.", vbExclamation, "QMS"
    Else
        Shell "python """ & p & """", vbNormalFocus
    End If
End Sub

' ── RIBBON CALLBACKS ─────────────────────────────────────────────────────────

Public Sub GetDocStatusLabel(control As IRibbonControl, ByRef label)
    Dim docID As String: docID = GetDocID()
    If docID = "" Then label = "Not a QMS Document": Exit Sub
    If Not ServerRunning() Then label = "Server Offline": Exit Sub
    Dim resp As String: resp = APIGet("/documents/" & docID)
    label = docID & "  Rev " & JV(resp, "version") & "  [" & JV(resp, "status") & "]"
End Sub

Public Sub GetRouteStatusLabel(control As IRibbonControl, ByRef label)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then label = "": Exit Sub
    Dim resp As String: resp = APIGet("/routing/queue?doc_id=" & docID & "&status=PENDING")
    If InStr(resp, "route_id") > 0 Then
        label = "⚡ Route Active"
    Else
        label = "No Active Route"
    End If
End Sub

Public Sub GetNotifCountLabel(control As IRibbonControl, ByRef label)
    If Not ServerRunning() Then label = "": Exit Sub
    Dim cfg As String: cfg = APIGet("/config")
    Dim stats As String: stats = APIGet("/stats")
    Dim cnt As String: cnt = JV(stats, "unread_notifs")
    If cnt = "" Or cnt = "0" Then
        label = "No new notifications"
    Else
        label = cnt & " unread notification(s)"
    End If
End Sub

Public Sub GetSubmitEnabled(control As IRibbonControl, ByRef enabled)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then enabled = False: Exit Sub
    enabled = (JV(APIGet("/documents/" & docID), "status") = "DRAFT")
End Sub

Public Sub GetApprovalEnabled(control As IRibbonControl, ByRef enabled)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then enabled = False: Exit Sub
    enabled = (JV(APIGet("/documents/" & docID), "status") = "IN_REVIEW")
End Sub

Public Sub GetCompleteReviewEnabled(control As IRibbonControl, ByRef enabled)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then enabled = False: Exit Sub
    Dim qresp As String: qresp = APIGet("/routing/queue?doc_id=" & docID & "&status=PENDING")
    Dim cfg As String: cfg = APIGet("/config")
    Dim me As String: me = LCase(JV(cfg, "current_user"))
    Dim assignee As String: assignee = LCase(JV(qresp, "assigned_to_name"))
    enabled = (assignee = me And JV(qresp, "route_type") = "REVIEW")
End Sub

Public Sub GetRecallEnabled(control As IRibbonControl, ByRef enabled)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then enabled = False: Exit Sub
    Dim qresp As String: qresp = APIGet("/routing/queue?doc_id=" & docID & "&status=PENDING")
    enabled = (InStr(qresp, "route_id") > 0)
End Sub
' ============================================================
' QMS Word Ribbon v1.2 — CR (Change Request) Support
' Additions to QMS_WordRibbon_v1_1.bas
' Add these subs to the existing module — do not replace
' ============================================================

' ── CR RIBBON BUTTONS ────────────────────────────────────────────────────────

' Called by ribbon: Show CR Info for this document
Public Sub QMS_ShowCRInfo(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    Dim resp As String: resp = APIGet("/documents/" & docID)
    Dim crID As String: crID = JV(resp, "cr_id")
    If crID = "" Or crID = "N/A" Then
        MsgBox "No CR is attached to " & docID & "." & vbCrLf & vbCrLf & _
               "Use 'Attach CR' in the ribbon to link this document to a Change Request.", _
               vbInformation, "QMS — No CR Attached"
        Exit Sub
    End If
    ' Get CR details
    Dim crResp As String: crResp = APIGet("/cr/" & crID)
    Dim crStatus As String: crStatus = JV(crResp, "status")
    Dim crTitle  As String: crTitle  = JV(crResp, "title")
    Dim crType   As String: crType   = JV(crResp, "change_type")
    Dim crBy     As String: crBy     = JV(crResp, "approved_by")
    Dim crEff    As String: crEff    = JV(crResp, "target_effective_date")
    Dim crActEff As String: crActEff = JV(crResp, "actual_effective_date")
    Dim linked   As String: linked   = JV(crResp, "linked_doc_ids")
    MsgBox "Change Request: " & crID & vbCrLf & _
           "Title:   " & crTitle & vbCrLf & _
           "Type:    " & crType & vbCrLf & _
           "Status:  " & crStatus & vbCrLf & _
           IIf(crBy <> "", "Approved by: " & crBy & vbCrLf, "") & _
           IIf(crEff <> "", "Target Effective: " & crEff & vbCrLf, "") & _
           IIf(crActEff <> "", "Actual Effective: " & crActEff & vbCrLf, "") & _
           "Linked Documents: " & linked, _
           vbInformation, "QMS — CR Info: " & crID
End Sub

' Called by ribbon: Attach a CR to this document
Public Sub QMS_AttachCR(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    ' Show existing CR if any
    Dim resp As String: resp = APIGet("/documents/" & docID)
    Dim existing As String: existing = JV(resp, "cr_id")
    Dim prompt As String
    If existing <> "" And existing <> "N/A" Then
        prompt = "Current CR: " & existing & vbCrLf & "Enter new CR number to reassign:"
    Else
        prompt = "Enter the CR number to attach to " & docID & ":"
    End If
    Dim crID As String
    crID = InputBox(prompt, "QMS — Attach CR", IIf(existing <> "", existing, "CR-"))
    If crID = "" Then Exit Sub
    ' Verify CR exists
    Dim crResp As String: crResp = APIGet("/cr/" & crID)
    If InStr(crResp, """error""") > 0 Then
        MsgBox "CR " & crID & " not found in the system." & vbCrLf & _
               "Create it first in the QMS Desktop App → Change Requests.", _
               vbExclamation, "QMS — CR Not Found"
        Exit Sub
    End If
    Dim body As String
    body = "{""cr_id"":""" & crID & """,""user"":""" & GetCurrentUser() & """}"
    Dim result As String: result = APIPost("/documents/" & docID & "/attach-cr", body)
    If JV(result, "ok") = "true" Then
        MsgBox docID & " has been linked to " & crID & "." & vbCrLf & vbCrLf & _
               "The CR number is now recorded in the document register." & vbCrLf & _
               "Update the CR Number field in the document header manually.", _
               vbInformation, "QMS — CR Attached"
    Else
        MsgBox "Error: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' Called by ribbon: Create a new CR and attach to this document
Public Sub QMS_CreateAndAttachCR(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "This is not a registered QMS document.", vbExclamation, "QMS": Exit Sub
    End If
    ' Collect CR info
    Dim crTitle As String
    crTitle = InputBox("CR Title (brief description of the change):", "QMS — New CR", "")
    If crTitle = "" Then Exit Sub
    Dim crDesc As String
    crDesc = InputBox("Description of change:", "QMS — CR Description", "")
    Dim crReason As String
    crReason = InputBox("Reason / justification for this change:", "QMS — CR Reason", "")
    Dim crType As String
    crType = InputBox("Change type:" & vbCrLf & _
                      "Process Change / Document Correction / Regulatory Update /" & vbCrLf & _
                      "Product Change / Supplier Change / CAPA-Driven / Other",  _
                      "QMS — Change Type", "Process Change")
    If crType = "" Then crType = "Process Change"
    Dim effDate As String
    effDate = InputBox("Target effective date (YYYY-MM-DD, leave blank to set later):", _
                       "QMS — Effective Date", "")
    Dim trainingReq As Integer
    trainingReq = MsgBox("Is training required before effectivity?", _
                          vbYesNo + vbQuestion, "QMS — Training Required")
    Dim trainingNotes As String
    If trainingReq = vbYes Then
        trainingNotes = InputBox("Training notes (who needs training, by when):", _
                                  "QMS — Training Notes", "")
    End If
    ' Create CR
    Dim body As String
    body = "{""title"":""" & Replace(crTitle, """", "'") & """," & _
           """description"":""" & Replace(crDesc, """", "'") & """," & _
           """reason"":""" & Replace(crReason, """", "'") & """," & _
           """change_type"":""" & crType & """," & _
           """initiator"":""" & GetCurrentUser() & """," & _
           """initiator_email"":""" & GetCurrentEmail() & """," & _
           """linked_doc_ids"":[""" & docID & """]," & _
           """target_effective_date"":""" & effDate & """," & _
           """training_required"":""" & IIf(trainingReq = vbYes, "YES", "NO") & """," & _
           """training_notes"":""" & Replace(trainingNotes, """", "'") & """}"
    Dim result As String: result = APIPost("/cr/new", body)
    If JV(result, "ok") = "true" Then
        ' Extract cr_id from nested response
        Dim crPos As Long: crPos = InStr(result, """cr_id"": """)
        Dim newCrID As String
        If crPos > 0 Then
            crPos = crPos + 10
            Dim crEnd As Long: crEnd = InStr(crPos, result, """")
            newCrID = Mid(result, crPos, crEnd - crPos)
        End If
        ' Attach to document
        Dim body2 As String
        body2 = "{""cr_id"":""" & newCrID & """,""user"":""" & GetCurrentUser() & """}"
        APIPost "/documents/" & docID & "/attach-cr", body2
        MsgBox "CR created: " & newCrID & vbCrLf & vbCrLf & _
               "Linked to: " & docID & vbCrLf & _
               "CR Form document generated in 11_CHANGE_REQUESTS/Draft/" & vbCrLf & vbCrLf & _
               "Update the CR Number field in this document's header to: " & newCrID, _
               vbInformation, "QMS — CR Created & Linked"
    Else
        MsgBox "Error creating CR: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' Called by ribbon: Make CR Effective (QA Lead function)
Public Sub QMS_MakeCREffective(control As IRibbonControl)
    If Not CheckServer() Then Exit Sub
    Dim docID As String: docID = GetDocID()
    If docID = "" Then
        MsgBox "Open a QMS document to identify its CR.", vbExclamation, "QMS": Exit Sub
    End If
    Dim resp As String: resp = APIGet("/documents/" & docID)
    Dim crID As String: crID = JV(resp, "cr_id")
    Dim docStatus As String: docStatus = JV(resp, "status")
    If crID = "" Then
        crID = InputBox("Enter CR number to make effective:", "QMS — Make Effective", "CR-")
        If crID = "" Then Exit Sub
    End If
    If docStatus <> "APPROVED_PENDING" Then
        MsgBox "This document is not in APPROVED_PENDING status." & vbCrLf & _
               "Current status: " & docStatus & vbCrLf & vbCrLf & _
               "Only APPROVED_PENDING documents can be made effective.", _
               vbExclamation, "QMS"
        Exit Sub
    End If
    ' Get CR and show what will be affected
    Dim crResp As String: crResp = APIGet("/cr/" & crID)
    Dim linked As String: linked = JV(crResp, "linked_doc_ids")
    Dim confirm As Integer
    confirm = MsgBox("Make " & crID & " EFFECTIVE?" & vbCrLf & vbCrLf & _
                     "Linked documents: " & linked & vbCrLf & vbCrLf & _
                     "All linked documents will become EFFECTIVE simultaneously." & vbCrLf & _
                     "Prior versions will be archived as OBSOLETE." & vbCrLf & vbCrLf & _
                     "This action cannot be undone.", _
                     vbYesNo + vbCritical, "QMS — Confirm Make Effective")
    If confirm <> vbYes Then Exit Sub
    Dim effDate As String
    effDate = InputBox("Effective date (YYYY-MM-DD, leave blank for today):", _
                       "QMS — Effective Date", Format(Now, "yyyy-mm-dd"))
    Dim body As String
    body = "{""user"":""" & GetCurrentUser() & """," & _
           """effective_date"":""" & effDate & """}"
    Dim result As String: result = APIPost("/cr/" & crID & "/make-effective", body)
    If JV(result, "ok") = "true" Then
        MsgBox crID & " is now EFFECTIVE as of " & JV(result, "effective_date") & "." & vbCrLf & vbCrLf & _
               "All linked documents are now EFFECTIVE." & vbCrLf & _
               "Prior versions have been archived." & vbCrLf & _
               "Team has been notified." & vbCrLf & vbCrLf & _
               "Close and reopen the document to see the updated status.", _
               vbInformation, "QMS — Effective"
        ActiveDocument.Close SaveChanges:=False
    Else
        MsgBox "Error: " & JV(result, "error"), vbCritical, "QMS"
    End If
End Sub

' ── RIBBON CALLBACKS FOR CR ───────────────────────────────────────────────────

Public Sub GetCRLabel(control As IRibbonControl, ByRef label)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then label = "No CR": Exit Sub
    Dim resp As String: resp = APIGet("/documents/" & docID)
    Dim crID As String: crID = JV(resp, "cr_id")
    If crID = "" Or crID = "N/A" Then
        label = "No CR Attached"
    Else
        label = "CR: " & crID
    End If
End Sub

Public Sub GetAttachCREnabled(control As IRibbonControl, ByRef enabled)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then enabled = False: Exit Sub
    ' Can attach CR when in DRAFT or IN_REVIEW
    Dim resp As String: resp = APIGet("/documents/" & docID)
    Dim status As String: status = JV(resp, "status")
    enabled = (status = "DRAFT" Or status = "IN_REVIEW")
End Sub

Public Sub GetMakeEffectiveEnabled(control As IRibbonControl, ByRef enabled)
    Dim docID As String: docID = GetDocID()
    If docID = "" Or Not ServerRunning() Then enabled = False: Exit Sub
    Dim resp As String: resp = APIGet("/documents/" & docID)
    enabled = (JV(resp, "status") = "APPROVED_PENDING")
End Sub
