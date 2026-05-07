' ============================================================
' QMS Excel Ribbon — VBA Module
' Save as a module inside QMS_RiskRegister.xltm
' Handles: Risk Registers, Design Traceability Matrices
' ============================================================

Option Explicit

Private Const API_BASE As String = "http://127.0.0.1:5151"

Private Function APIGet(endpoint As String) As String
    On Error GoTo ErrHandler
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP.6.0")
    http.Open "GET", API_BASE & endpoint, False
    http.send
    APIGet = http.responseText
    Exit Function
ErrHandler:
    APIGet = "{""error"":""Connection failed""}"
End Function

Private Function APIPost(endpoint As String, body As String) As String
    On Error GoTo ErrHandler
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP.6.0")
    http.Open "POST", API_BASE & endpoint, False
    http.setRequestHeader "Content-Type", "application/json"
    http.send body
    APIPost = http.responseText
    Exit Function
ErrHandler:
    APIPost = "{""error"":""Connection failed""}"
End Function

Private Function ParseJSON_Value(json As String, key As String) As String
    Dim pattern As String
    Dim pos As Long, endPos As Long
    pattern = """" & key & """" & ":"
    pos = InStr(json, pattern)
    If pos = 0 Then ParseJSON_Value = "": Exit Function
    pos = pos + Len(pattern)
    Do While Mid(json, pos, 1) = " " Or Mid(json, pos, 1) = Chr(9)
        pos = pos + 1
    Loop
    If Mid(json, pos, 1) = """" Then
        pos = pos + 1
        endPos = InStr(pos, json, """")
        ParseJSON_Value = Mid(json, pos, endPos - pos)
    Else
        endPos = pos
        Do While Mid(json, endPos, 1) <> "," And Mid(json, endPos, 1) <> "}" And endPos < Len(json)
            endPos = endPos + 1
        Loop
        ParseJSON_Value = Trim(Mid(json, pos, endPos - pos))
    End If
End Function

Private Function ServerRunning() As Boolean
    On Error GoTo No
    Dim http As Object
    Set http = CreateObject("MSXML2.XMLHTTP.6.0")
    http.Open "GET", API_BASE & "/ping", False
    http.send
    ServerRunning = (http.Status = 200)
    Exit Function
No: ServerRunning = False
End Function

' ── RISK REGISTER FUNCTIONS ──────────────────────────────────────────────────

' Auto-calculate Risk Priority Number (RPN) or Risk Level
' Severity × Probability → Risk Level per ISO 14971 Annex E
Public Sub QMS_CalcRiskLevel(control As IRibbonControl)
    Dim ws As Worksheet
    Set ws = ActiveSheet
    ' Expects columns: A=Hazard, B=Situation, C=Harm, D=Severity(1-5), E=Probability(1-5)
    ' Writes to: F=RPN, G=Risk Level, H=Acceptability
    Dim lastRow As Long
    lastRow = ws.Cells(ws.Rows.Count, "A").End(xlUp).Row
    Dim i As Long
    For i = 2 To lastRow  ' Skip header row
        Dim sev As Integer, prob As Integer, rpn As Integer
        On Error Resume Next
        sev  = CInt(ws.Cells(i, 4).Value)
        prob = CInt(ws.Cells(i, 5).Value)
        On Error GoTo 0
        If sev > 0 And prob > 0 Then
            rpn = sev * prob
            ws.Cells(i, 6).Value = rpn
            ' Risk level per ISO 14971 matrix
            Dim level As String, accept As String
            Select Case rpn
                Case 1 To 3:   level = "LOW":      accept = "Acceptable"
                Case 4 To 8:   level = "MEDIUM":   accept = "ALARP Review Required"
                Case 9 To 15:  level = "HIGH":     accept = "Risk Control Required"
                Case 16 To 25: level = "CRITICAL": accept = "Not Acceptable"
                Case Else:     level = "—":        accept = "—"
            End Select
            ws.Cells(i, 7).Value = level
            ws.Cells(i, 8).Value = accept
            ' Color coding
            Select Case level
                Case "LOW":      ws.Cells(i, 7).Interior.Color = RGB(198, 239, 206)  ' Green
                Case "MEDIUM":   ws.Cells(i, 7).Interior.Color = RGB(255, 235, 156)  ' Yellow
                Case "HIGH":     ws.Cells(i, 7).Interior.Color = RGB(255, 199, 206)  ' Red-light
                Case "CRITICAL": ws.Cells(i, 7).Interior.Color = RGB(180,  50,  50)  ' Dark red
            End Select
        End If
    Next i
    MsgBox "Risk levels calculated for " & (lastRow - 1) & " rows." & vbCrLf & _
           "Review all HIGH and CRITICAL items for risk control measures.", _
           vbInformation, "QMS — Risk Calculation Complete"
End Sub

' Create a new Risk Register sheet from the template layout
Public Sub QMS_NewRiskRegister(control As IRibbonControl)
    Dim wb As Workbook
    Set wb = ActiveWorkbook
    Dim wsName As String
    wsName = InputBox("Enter device / project name for this risk register:", _
                      "QMS — New Risk Register", "Device Name")
    If wsName = "" Then Exit Sub
    Dim ws As Worksheet
    Set ws = wb.Sheets.Add(After:=wb.Sheets(wb.Sheets.Count))
    ws.Name = Left("RR_" & wsName, 31)  ' Sheet name limit

    ' Headers
    Dim headers As Variant
    headers = Array("Hazard ID", "Hazard", "Hazardous Situation", "Harm", _
                    "Severity (1-5)", "Probability (1-5)", "RPN", _
                    "Risk Level", "Acceptability", "Risk Control Measure", _
                    "Control Type", "Residual Severity", "Residual Probability", _
                    "Residual RPN", "Residual Level", "Verification Method", _
                    "ISO 14971 Clause", "Status", "Notes")
    Dim col As Integer
    For col = 0 To UBound(headers)
        With ws.Cells(1, col + 1)
            .Value = headers(col)
            .Font.Bold = True
            .Font.Color = RGB(255, 255, 255)
            .Interior.Color = RGB(0, 63, 127)
            .WrapText = True
        End With
    Next col

    ' Freeze header row
    ws.Rows(2).Select
    ActiveWindow.FreezePanes = True
    ws.Cells(2, 1).Select

    ' Add reference row
    ws.Cells(2, 1).Value = "H-001"
    ws.Cells(2, 17).Value = "Cl. 4-10"

    ' Auto-fit columns
    ws.Columns.AutoFit

    ' Add title
    ws.Rows(1).RowHeight = 40

    MsgBox "Risk Register created: " & ws.Name & vbCrLf & vbCrLf & _
           "Column guide:" & vbCrLf & _
           "Severity 1=Negligible, 2=Minor, 3=Serious, 4=Critical, 5=Catastrophic" & vbCrLf & _
           "Probability 1=Incredible, 2=Remote, 3=Occasional, 4=Probable, 5=Frequent", _
           vbInformation, "QMS — Risk Register Ready"
End Sub

' Create a Design Traceability Matrix (DTM)
Public Sub QMS_NewTraceabilityMatrix(control As IRibbonControl)
    Dim wb As Workbook
    Set wb = ActiveWorkbook
    Dim wsName As String
    wsName = InputBox("Enter device / project name for this traceability matrix:", _
                      "QMS — New Traceability Matrix", "Device Name")
    If wsName = "" Then Exit Sub
    Dim ws As Worksheet
    Set ws = wb.Sheets.Add(After:=wb.Sheets(wb.Sheets.Count))
    ws.Name = Left("DTM_" & wsName, 31)

    Dim headers As Variant
    headers = Array("Req ID", "User Need", "Design Input", "Design Output", _
                    "Verification Method", "Verification Record", "Validation Method", _
                    "Validation Record", "Risk ID (RM Ref)", "ISO 13485 §7.3 Stage", _
                    "Status", "Notes")
    Dim col As Integer
    For col = 0 To UBound(headers)
        With ws.Cells(1, col + 1)
            .Value = headers(col)
            .Font.Bold = True
            .Font.Color = RGB(255, 255, 255)
            .Interior.Color = RGB(42, 42, 80)
            .WrapText = True
        End With
    Next col

    ws.Rows(1).RowHeight = 40
    ws.Rows(2).Select
    ActiveWindow.FreezePanes = True
    ws.Cells(2, 1).Select
    ws.Cells(2, 1).Value = "REQ-001"
    ws.Cells(2, 10).Value = "7.3.3 Design Input"
    ws.Columns.AutoFit

    MsgBox "Design Traceability Matrix created: " & ws.Name & vbCrLf & vbCrLf & _
           "Each row traces a user need through:" & vbCrLf & _
           "Design Input → Output → Verification → Validation" & vbCrLf & _
           "Cross-reference risk IDs from your Risk Register (RM-xxx).", _
           vbInformation, "QMS — Traceability Matrix Ready"
End Sub

' Register the current Excel workbook as a QMS document
Public Sub QMS_RegisterWorkbook(control As IRibbonControl)
    If Not ServerRunning() Then
        MsgBox "QMS Server is not running. Please launch the QMS Desktop App first.", _
               vbExclamation, "QMS"
        Exit Sub
    End If
    Dim dtype As String
    dtype = InputBox("Document type prefix (RM=Risk Mgmt, DC=Design Control, FM=Form):", _
                     "QMS — Register Document", "RM")
    If dtype = "" Then Exit Sub
    Dim dtitle As String
    dtitle = InputBox("Document title:", "QMS — Title", ActiveWorkbook.Name)
    If dtitle = "" Then Exit Sub
    Dim owner As String
    owner = InputBox("Owner / Author:", "QMS — Owner", Environ("USERNAME"))
    If owner = "" Then Exit Sub
    Dim c14 As String
    c14 = InputBox("ISO 14971 clause(s):", "QMS — ISO 14971", "4, 5, 6, 7, 8, 9, 10")
    Dim body As String
    body = "{""type"":""" & UCase(dtype) & """,""title"":""" & dtitle & """," & _
           """owner"":""" & owner & """,""clause_14971"":""" & c14 & """}"
    Dim response As String
    response = APIPost("/documents/new", body)
    If ParseJSON_Value(response, "ok") = "true" Then
        MsgBox "Registered as: " & ParseJSON_Value(response, "doc_id") & vbCrLf & _
               "Document template created in the QMS Draft folder." & vbCrLf & vbCrLf & _
               "Note: Save your Excel file into the same Draft folder using the QMS naming convention.", _
               vbInformation, "QMS — Registered"
    Else
        MsgBox "Error: " & ParseJSON_Value(response, "error"), vbCritical, "QMS Error"
    End If
End Sub

' Show QMS documents list filtered to RM / DC types
Public Sub QMS_ShowRiskDocs(control As IRibbonControl)
    If Not ServerRunning() Then
        MsgBox "QMS Server is not running.", vbExclamation, "QMS"
        Exit Sub
    End If
    Dim response As String
    response = APIGet("/documents?type=RM&status=APPROVED")
    MsgBox "Approved Risk Management documents:" & vbCrLf & vbCrLf & _
           "(Open the QMS Desktop App for full document list and actions)", _
           vbInformation, "QMS — Risk Documents"
End Sub
