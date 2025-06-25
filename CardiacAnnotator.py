from slicer.ScriptedLoadableModule import *
import ctk
import qt
import slicer
import os 
import pandas as pd
import time

class CardiacAnnotator(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "CardiacAnnotator"
        self.parent.categories = ["Cardiac"]
        self.parent.dependencies = []
        self.parent.contributors = ["JD"]
        iconPath = os.path.join(os.path.dirname(__file__), "CardiacAnnotator.png")
        self.parent.icon = qt.QIcon(iconPath)

class CardiacAnnotatorWidget(ScriptedLoadableModuleWidget):   
 
    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = CardiacAnnotatorLogic()

        # =============================================================================
        # CASE NAVIGATOR SECTION
        # =============================================================================  
        landmarkCollapsibleButton = ctk.ctkCollapsibleButton()
        landmarkCollapsibleButton.text = "Case Navigator"
        self.layout.addWidget(landmarkCollapsibleButton)
        navigatorLayout = qt.QVBoxLayout(landmarkCollapsibleButton)
        
        # Load Cases Subsection
        self.loadCasesButton = qt.QPushButton("Load cases folder")
        navigatorLayout.addWidget(self.loadCasesButton)

        # Active Case Subsection
        self.activeCaseLabel = qt.QLabel("Active case:")
        self.activeCaseLabel.hide()  
        navigatorLayout.addWidget(self.activeCaseLabel)
        
        self.activeCaseWidget = qt.QLabel()
        self.activeCaseWidget.hide()
        self.activeCaseWidget.setAlignment(qt.Qt.AlignCenter)
        self.activeCaseWidget.setMaximumHeight(20)
        self.activeCaseWidget.setStyleSheet("border: 1px solid gray;font-weight: bold;")
        navigatorLayout.addWidget(self.activeCaseWidget) 

        # Case List Collapsible Subsection
        self.caseListCollapsible = ctk.ctkCollapsibleButton()
        self.caseListCollapsible.text = "Case list"
        self.caseListCollapsible.collapsed = False
        self.caseListCollapsible.hide()
        navigatorLayout.addWidget(self.caseListCollapsible)
        
        # Case list layout (inside collapsible subsection)
        caseListLayout = qt.QVBoxLayout(self.caseListCollapsible)
        
        # Horizontal layout for list and button
        caseLayout = qt.QHBoxLayout()
        
        # Case list widget
        self.caseListWidget = qt.QListWidget()
        self.caseListWidget.setMaximumHeight(100)
        self.caseListWidget.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded)
        caseLayout.addWidget(self.caseListWidget)
        
        # Select case button
        self.selectCaseButton = qt.QPushButton("Select Case")
        self.selectCaseButton.setMaximumWidth(100)
        caseLayout.addWidget(self.selectCaseButton)
        
        # Add horizontal layout to case list layout
        caseListLayout.addLayout(caseLayout)
        
        # Connect signals
        self.selectCaseButton.connect('clicked()', self.onSelectCase)
        self.loadCasesButton.connect('clicked()', self.onLoadCasesClicked)
        
   
        # =============================================================================
        # LANDMARKS MARKING SECTION
        # =============================================================================
        landmarksCollapsibleButton = ctk.ctkCollapsibleButton()
        landmarksCollapsibleButton.text = "Landmarks Marking"
        landmarksCollapsibleButton.collapsed = True
        self.layout.addWidget(landmarksCollapsibleButton)
        landmarksLayout = qt.QVBoxLayout(landmarksCollapsibleButton)

        # Status label
        self.landmarkStatusLabel = qt.QLabel("No case loaded")
        self.landmarkStatusLabel.setStyleSheet("color: gray; font-style: italic;")
        landmarksLayout.addWidget(self.landmarkStatusLabel)

        # Current landmark section
        currentLandmarkFrame = qt.QFrame()
        currentLandmarkFrame.setStyleSheet("QFrame { border: 1px solid #cccccc; border-radius: 5px; padding: 5px; }")
        landmarksLayout.addWidget(currentLandmarkFrame)
        currentLandmarkLayout = qt.QVBoxLayout(currentLandmarkFrame)

        # Current landmark label
        self.currentLandmarkLabel = qt.QLabel("Current Landmark: None")
        self.currentLandmarkLabel.setStyleSheet("font-weight: bold; color: #2196F3;")
        currentLandmarkLayout.addWidget(self.currentLandmarkLabel)

        # Landmark selection
        landmarkSelectionLayout = qt.QHBoxLayout()

        # Landmark dropdown
        self.landmarkComboBox = qt.QComboBox()
        self.landmarkComboBox.addItems([
            "Left Coronary Cusp Nadir",
            "Right Coronary Cusp Nadir", 
            "Non Coronary Cusp Nadir",
            "Right-Left Commissure",
            "Right-Non Commissure",
            "Left-Non Commissure",
            "Left Coronary Ostium Base",
            "Right Coronary Ostium Base",
            "Annulus Contour (Spline)"
        ])
        landmarkSelectionLayout.addWidget(self.landmarkComboBox)
        self.landmarkComboBox.currentTextChanged.connect(self.onLandmarkSelectionChanged)

        # Start/Stop landmark button
        self.startStopButton = qt.QPushButton("Start Landmark")
        self.startStopButton.setStyleSheet("QPushButton { background-color: #4CAF50; color: black; font-weight: bold; }")
        self.startStopButton.setEnabled(False)  # Disabled until case is loaded
        landmarkSelectionLayout.addWidget(self.startStopButton)

        landmarksLayout.addLayout(landmarkSelectionLayout)

        # Progress tracking
        progressFrame = qt.QFrame()
        progressFrame.setStyleSheet("QFrame { border: 1px solid #e0e0e0; border-radius: 3px; padding: 3px; }")
        landmarksLayout.addWidget(progressFrame)
        progressLayout = qt.QVBoxLayout(progressFrame)

        progressLabel = qt.QLabel("Landmark Progress:")
        progressLabel.setStyleSheet("font-weight: bold; font-size: 10pt;")
        progressLayout.addWidget(progressLabel)

        # Progress list
        self.landmarkProgressList = qt.QListWidget()
        self.landmarkProgressList.setMaximumHeight(120)
        self.landmarkProgressList.setAlternatingRowColors(True)
        progressLayout.addWidget(self.landmarkProgressList)

        # Action buttons
        actionButtonsLayout = qt.QHBoxLayout()

        self.markCompleteButton = qt.QPushButton("Mark Complete")
        self.markCompleteButton.setStyleSheet("QPushButton { background-color: #FF9800; color: black; font-weight: bold;}")
        self.markCompleteButton.setEnabled(False)
        actionButtonsLayout.addWidget(self.markCompleteButton)

        self.resetLandmarkButton = qt.QPushButton("Reset Current")
        self.resetLandmarkButton.setStyleSheet("QPushButton { background-color: #f44336; color: black; font-weight: bold;}")
        self.resetLandmarkButton.setEnabled(False)
        actionButtonsLayout.addWidget(self.resetLandmarkButton)

        landmarksLayout.addLayout(actionButtonsLayout)

        # Notes section
        notesLabel = qt.QLabel("Notes:")
        notesLabel.setStyleSheet("font-weight: bold;")
        landmarksLayout.addWidget(notesLabel)

        self.notesTextEdit = qt.QTextEdit()
        self.notesTextEdit.setMaximumHeight(60)
        self.notesTextEdit.setPlaceholderText("Add notes for current landmark...")
        landmarksLayout.addWidget(self.notesTextEdit)

        # Connect landmark signals
        self.startStopButton.connect('clicked()', self.onStartStopLandmark)
        self.markCompleteButton.connect('clicked()', self.onMarkComplete)
        self.resetLandmarkButton.connect('clicked()', self.onResetLandmark)

        # Timer for updating display
        self.timer = qt.QTimer()
        self.timer.timeout.connect(self.updateTimerDisplay)
        self.current_landmark_active = False

        # For putting it at the top
        self.layout.addStretch(1)
        self.layout.setAlignment(qt.Qt.AlignTop)

    def updateCaseList(self, next_cases):
        # self.caseLabel.show()
        self.caseListWidget.clear()
        
        for case in next_cases:
            # Check if case is in progress
            case_row = self.logic.progress_df[self.logic.progress_df['Case_ID'] == case]
            if not case_row.empty and case_row.iloc[0]['Status'] == 'in_progress':
                display_text = f"{case} (in progress)"
            else:
                display_text = case
                
            self.caseListWidget.addItem(display_text)
        
        # self.caseListWidget.show()
        # self.selectCaseButton.show()
        # self.activeCaseLabel.show() 
        self.caseListCollapsible.show()

    def onSelectCase(self):
        selected_item = self.caseListWidget.currentItem()
        if selected_item:
            display_text = selected_item.text()
            # Remove "(in progress)" if present
            case_name = display_text.replace(" (in progress)", "")
            print(f"Starting work on: {case_name}")
            self.logic.loadCase(case_name)
            self.activeCaseWidget.setText(case_name)
            self.activeCaseWidget.show()
            self.activeCaseLabel.show()   
            self.enableLandmarkSection(case_name)     
        
    def onLoadCasesClicked(self):
        # Always use last saved directory as default
        settings = qt.QSettings()
        default_dir = settings.value("CardiacAnnotator/lastDirectory", "")
        
        selected_dir = qt.QFileDialog.getExistingDirectory(None, "Select TAVI Dataset Directory", default_dir)
        
        if selected_dir:
            # self.loadCasesButton.setText(selected_dir) # commented to keep "Load cases" text
            # Always save the selected directory
            settings.setValue("CardiacAnnotator/lastDirectory", selected_dir)
            next_case = self.logic.initializeProgressTracking(selected_dir)  
            next_cases = self.logic.getNextCases()  # You'll need this method in Logic
            self.updateCaseList(next_cases)            
            
    def _logActivity(self, activity_type, name, action):
        """Shared logging method"""
        if hasattr(self.logic, 'current_log_manager') and self.logic.current_log_manager:
            self.logic.current_log_manager.write_entry(f"{action} {activity_type}: {name}")

    def _onStartStopActivity(self, activity_type, combo_box, status_attr, label_widget, button_widget, complete_button, reset_button):
        """Shared start/stop method for landmarks and segments"""
        if not getattr(self, status_attr):
            # Start activity
            activity_name = combo_box.currentText
            self.logic.startActivityTimer(activity_type, activity_name)
            self._logActivity(activity_type, activity_name, "Started")

            if activity_type == "landmark":
                self.enableLandmarkPlacement(activity_name)
            elif activity_type == "segment":
            # Different handling for segments
                pass
            
            setattr(self, status_attr, True)
            label_widget.setText(f"Current {activity_type.title()}: {activity_name}")
            button_widget.setText(f"Stop {activity_type.title()}")
            button_widget.setStyleSheet("QPushButton { background-color: #f44336; color: #000000; font-weight: bold; }")
            complete_button.setEnabled(True)
            reset_button.setEnabled(True)
            
            # Update progress list
            getattr(self, f'update{activity_type.title()}ProgressList')()
            
        else:
            # Stop activity
            activity_name = getattr(self.logic, f'current_{activity_type}')
            self.logic.stopActivityTimer(activity_type)
            self._logActivity(activity_type, activity_name, "Stopped")

            if activity_type == "landmark":
                # Disable placement mode
                interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
                interactionNode.SetCurrentInteractionMode(interactionNode.ViewTransform)
            
            setattr(self, status_attr, False)
            label_widget.setText(f"Current {activity_type.title()}: None")
            button_widget.setText(f"Start {activity_type.title()}")
            button_widget.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")
            complete_button.setEnabled(False)
            reset_button.setEnabled(False)

    def onStartStopLandmark(self):
        self._onStartStopActivity("landmark", self.landmarkComboBox, "current_landmark_active", 
                                self.currentLandmarkLabel, self.startStopButton,
                                self.markCompleteButton, self.resetLandmarkButton)

    def onMarkComplete(self):
        if self.current_landmark_active:
            landmark_name = self.landmarkComboBox.currentText
            self.logic.completeLandmark(landmark_name, self.notesTextEdit.toPlainText())
            self.onStartStopLandmark()  # Stop current landmark
            self.notesTextEdit.clear()  
            self.updateLandmarkProgressList()

    def onResetLandmark(self):
        if self.current_landmark_active:
            self.logic.resetCurrentLandmark()
            self.onStartStopLandmark()  # Stop current landmark
            self.notesTextEdit.clear()

    def updateTimerDisplay(self):
        if self.current_landmark_active and hasattr(self.logic, 'landmark_start_time'):
            elapsed = time.time() - self.logic.landmark_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.timerLabel.setText(f"Time: {minutes:02d}:{seconds:02d}")

    def updateLandmarkProgressList(self):
        self.landmarkProgressList.clear()
        if hasattr(self.logic, 'current_log_manager') and self.logic.current_log_manager:
            # Get landmark progress from logic
            progress = self.logic.getLandmarkProgress()
            for landmark, status in progress.items():
                item_text = f"{landmark}: {status}"
                self.landmarkProgressList.addItem(item_text)

    def enableLandmarkSection(self, case_name):
        """Enable landmark section when a case is loaded"""
        self.landmarkStatusLabel.setText(f"Ready for annotation: {case_name}")
        self.landmarkStatusLabel.setStyleSheet("color: green; font-style: normal; font-weight: bold;")
        self.startStopButton.setEnabled(True)
        self.updateLandmarkProgressList()

    def onLandmarkSelectionChanged(self):
        if self.current_landmark_active:
            # Auto-stop current landmark
            self.onStartStopLandmark()  # This will stop the current one
            self._logActivity("landmark", self.logic.current_landmark, "Auto-stopped (selection changed)")

    def enableLandmarkPlacement(self, landmark_name):
        # Create or get markups node
        if not hasattr(self.logic, 'markups_node') or not self.logic.markups_node:
            self.logic.markups_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
            self.logic.markups_node.SetName(f"Landmarks_{self.logic.current_case_name}")
            
            # Force scene update
            slicer.app.processEvents()
        
        # Set active markups node first  
        selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
        selectionNode.SetReferenceActivePlaceNodeID(self.logic.markups_node.GetID())
        
        # Enable placement mode
        interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
        interactionNode.SetCurrentInteractionMode(interactionNode.Place)
        interactionNode.SetPlaceModePersistence(1)


class CardiacAnnotatorLogic(ScriptedLoadableModuleLogic):

    def initializeProgressTracking(self, main_folder):
        self.main_folder = main_folder
        self.csv_path = os.path.join(main_folder, "progress_tracking.csv")
        
        # Load or create CSV
        if os.path.exists(self.csv_path):
            self.progress_df = pd.read_csv(self.csv_path, sep=";")
        else:
            # Create new CSV inline
            case_list = self.findAllTAVICases(main_folder)     
            print("###\n",case_list)   
            self.progress_df = pd.DataFrame({
                'Case_ID': case_list,
                'Status': ['not_started'] * len(case_list),
                'Date_Started': [''] * len(case_list),
                'Date_Completed': [''] * len(case_list),
                'Annotator': [''] * len(case_list),
                'Verified': ['No'] * len(case_list),
                'Cusp_Nadir_1_Time': [0] * len(case_list),
                'Cusp_Nadir_2_Time': [0] * len(case_list),
                'Commissure_1_Time': [0] * len(case_list),
                # ... etc for each landmark/segment
                'Total_Time': [0] * len(case_list)
            })
            self.progress_df.to_csv(self.csv_path, index=False, sep=";")
        
        # Find next case to work on
        next_case = self.findNextCase()
        return next_case if next_case else None
    
    def loadOrCreateProgressCSV(self, main_folder):
        # Load existing CSV or create new one
        pass

    def findNextCase(self):
        # Find first in_progress or not_started case
        pass

    def updateCaseStatus(self, case_id, status):
        # Update case status in CSV
        pass
    
    def findAllTAVICases(self, main_folder):
        case_list = []      
        for item in os.listdir(main_folder):
            if not (item.startswith('TAVI') and os.path.isdir(os.path.join(main_folder, item))):
                continue
                
            platipy_dir = os.path.join(main_folder, item, 'Platipy')
            if not os.path.exists(platipy_dir):
                continue
                
            # Check for 40pc.nii.gz files
            files = [f for f in os.listdir(platipy_dir) if f.endswith('40pc.nii.gz')]
            if files:
                case_list.append(item)
        
        return sorted(case_list)

    def startActivityTimer(self, activity_type, activity_name):
        setattr(self, f'current_{activity_type}', activity_name)
        setattr(self, f'{activity_type}_start_time', time.time())

    def stopActivityTimer(self, activity_type):
        if hasattr(self, f'{activity_type}_start_time'):
            elapsed = time.time() - getattr(self, f'{activity_type}_start_time')
            delattr(self, f'{activity_type}_start_time')

    def getNextCases(self):
        if not hasattr(self, 'progress_df'):
            return []
        
        # Get in_progress cases first, then not_started
        in_progress = self.progress_df[self.progress_df['Status'] == 'in_progress']['Case_ID'].tolist()
        not_started = self.progress_df[self.progress_df['Status'] == 'not_started']['Case_ID'].tolist()
        
        # Combine: in_progress first, then not_started
        pending_cases = in_progress + not_started
                
        return pending_cases
   
    def loadCase(self, case_name): 
        # Close previous log if exists
        if hasattr(self, 'current_log_manager') and self.current_log_manager:
            self.current_log_manager.close_case("switched")
        
        # Create new LogManager for this case
        case_folder = os.path.join(self.main_folder, case_name, 'Platipy')
        self.current_log_manager = self.LogManager(case_folder, case_name)
        self.current_log_manager.open_case(case_name)
        
        case_path = os.path.join(self.main_folder, case_name, 'Platipy', f'{case_name} 40pc.nii.gz')        
        slicer.util.loadVolume(case_path)        
        self.updateCaseStatus(case_name, "in_progress")        
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)

        # Create markups node for this case if it doesn't exist
        node_name = f"Landmarks_{case_name}"
        try:
            self.markups_node = slicer.util.getNode(node_name)
        except slicer.util.MRMLNodeNotFoundException:
            self.markups_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
            self.markups_node.SetName(node_name)
        
        self.current_case_name = case_name

    def updateCaseStatus(self, case_id, status):
        # Find the row for this case
        case_row_index = self.progress_df[self.progress_df['Case_ID'] == case_id].index
        
        if not case_row_index.empty:
            current_status = self.progress_df.loc[case_row_index[0], 'Status']
            
            # Only update if moving from not_started to in_progress
            if current_status == 'not_started' and status == 'in_progress':
                self.progress_df.loc[case_row_index[0], 'Status'] = status
                self.progress_df.loc[case_row_index[0], 'Date_Started'] = time.strftime("%Y-%m-%d %H:%M:%S")
                # Add annotator info if you want
                
                # Save CSV
                self.progress_df.to_csv(self.csv_path, index=False, sep=";")

    def completeLandmark(self, landmark_name, notes):
        # Add completion logic here
        if hasattr(self, 'current_log_manager') and self.current_log_manager:
            self.current_log_manager.write_entry(f"Completed landmark: {landmark_name} - Notes: {notes}")

    def resetCurrentLandmark(self):
        # Add reset logic here
        if hasattr(self, 'current_log_manager') and self.current_log_manager:
            self.current_log_manager.write_entry(f"Reset landmark: {self.current_landmark}")

    def getLandmarkProgress(self):
        # Return progress dictionary for display
        return {"Sample": "In Progress"}  # Replace with actual progress tracking


    class LogManager:

        def __init__(self, case_folder_path, case_name):
            self.log_path = os.path.join(case_folder_path, f"annotation log {case_name}.txt")
            self.current_task = None
            self.task_start_time = None
        
        def write_entry(self, message):
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"{timestamp} - {message}\n"
            
            # Create file if it doesn't exist, append if it does
            with open(self.log_path, 'a') as f:
                f.write(log_line)
        
        def open_case(self, case_name):
            if not os.path.exists(self.log_path):
                # New log file
                self.write_entry(f"=== {case_name} Annotation Log ===")
                self.write_entry("Case opened/loaded in Slicer")
            else:
                # Existing log - check if previous session ended cleanly
                with open(self.log_path, 'r') as f:
                    lines = f.readlines()
                
                if lines:
                    last_line = lines[-1].strip()
                    if not ("case closed" in last_line.lower() or "session ended" in last_line.lower() or "completed and closed" in last_line.lower()):
                        # Previous session ended abruptly
                        self.write_entry("Case reopened (previous session ended unexpectedly)")
                    else:
                        # Previous session ended cleanly
                        self.write_entry("Case reopened")
                else:
                    # Empty file
                    self.write_entry(f"=== {case_name} Annotation Log ===")
                    self.write_entry("Case opened/loaded in Slicer")
        
        def close_case(self, reason="switched"):
            if reason == "switched":
                self.write_entry(f"Case closed (switched to another case)")
            elif reason == "completed":
                self.write_entry("Case completed and closed")
            elif reason == "session_ended":
                self.write_entry("Case closed (session ended)")
            else:
                self.write_entry(f"Case closed ({reason})")
                
                def start_task(self, task_name):
                    # Start timer, write "started X" entry
                    0
                
                def complete_task(self):
                    # Calculate duration, write "completed X" entry
                    0




class CardiacAnnotatorTest(ScriptedLoadableModuleTest):
  def runTest(self):
    pass