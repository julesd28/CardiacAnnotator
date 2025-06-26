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
        self.caseListWidget.itemActivated.connect(self.onCaseListItemActivated)
        
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

        # Landmark selection
        landmarkSelectionLayout = qt.QHBoxLayout()

        # Lock/Unlock button
        self.lockUnlockButton = qt.QPushButton("")
        self.lockUnlockButton.setEnabled(False)
        landmarkSelectionLayout.addWidget(self.lockUnlockButton)

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
        self.landmarkProgressList.setMaximumHeight(130)
        self.landmarkProgressList.setAlternatingRowColors(True)
        self.landmarkProgressList.itemClicked.connect(self.onLandmarkItemClicked)
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

        # Connect landmark signals
        self.lockUnlockButton.connect('clicked()', self.onLockUnlockClicked)
        self.markCompleteButton.connect('clicked()', self.onMarkComplete)
        self.resetLandmarkButton.connect('clicked()', self.onResetLandmark)

        # Timer for updating display
        self.timer = qt.QTimer()
        self.timer.timeout.connect(self.updateTimerDisplay)
        self.current_landmark_active = False

        # =============================================================================
        # SAVE CASE BUTTON (standalone)
        # =============================================================================

        self.saveCaseButton = qt.QPushButton("Save Case")
        self.saveCaseButton.setStyleSheet("QPushButton {  color: white; font-weight: bold; padding: 8px; }")
        self.saveCaseButton.hide()  # Hidden until case is loaded
        self.layout.addWidget(self.saveCaseButton)

        # Connect save button
        self.saveCaseButton.connect('clicked()', self.onSaveCaseClicked)

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
        
        self.activeCaseLabel.show() 
        self.caseListCollapsible.show()

    def onSelectCase(self):
        selected_item = self.caseListWidget.currentItem()
        if selected_item:
            display_text = selected_item.text()
            # Remove "(in progress)" if present
            case_name = display_text.replace(" (in progress)", "")
            print(f"Starting work on: {case_name}")
            self.logic.widget_reference = self
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

    def onMarkComplete(self):
        if hasattr(self, 'selected_landmark'):
            landmark_name = self.selected_landmark
            self.logic.completeLandmark(landmark_name, "")
            
            # Lock the landmark
            self.logic.lockUnlockLandmark(landmark_name, lock=True)
            
            # Update UI
            self.updateActionButtons(landmark_name)
            self.updateLandmarkProgressList()

    def onResetLandmark(self):
        if hasattr(self, 'selected_landmark'):
            landmark_name = self.selected_landmark
            if landmark_name == "Annulus Contour (Spline)":
                self.logic.resetSpline()
            else:
                self.logic.resetCurrentLandmark()
            
            # Update UI
            self.updateActionButtons(landmark_name)
            self.updateLandmarkProgressList()

    def updateTimerDisplay(self):
        if self.current_landmark_active and hasattr(self.logic, 'landmark_start_time'):
            elapsed = time.time() - self.logic.landmark_start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.timerLabel.setText(f"Time: {minutes:02d}:{seconds:02d}")

    def updateLandmarkProgressList(self):
        self.landmarkProgressList.clear()
        if hasattr(self.logic, 'current_log_manager') and self.logic.current_log_manager:
            progress = self.logic.getLandmarkProgress()
            for landmark, status in progress.items():
                item_text = f"{landmark}: {status}"
                item = qt.QListWidgetItem(item_text)
                font = item.font()
                font.setPointSize(12)
                
                # Highlight if this is the currently selected landmark
                if hasattr(self, 'selected_landmark') and self.selected_landmark == landmark:
                    item.setBackground(qt.QColor(255, 235, 59, 100))  # Light yellow background
                    font.setBold(True)
                
                item.setFont(font)
                self.landmarkProgressList.addItem(item)
        
        self.landmarkProgressList.setStyleSheet("QListWidget { font-size: 12pt; }")

    def enableLandmarkSection(self, case_name):
        """Enable landmark section when a case is loaded"""
        self.landmarkStatusLabel.setText(f"Ready for annotation: {case_name}")
        self.landmarkStatusLabel.setStyleSheet("color: green; font-style: normal; font-weight: bold; font-size: 10pt;")
        self.lockUnlockButton.setEnabled(False)
        self.updateLandmarkProgressList()

    def onLandmarkSelectionChanged(self):
        if self.current_landmark_active:
            # Auto-stop current landmark
            self.onStartStopLandmark()  # This will stop the current one
            self._logActivity("landmark", self.logic.current_landmark, "Auto-stopped (selection changed)")

    def enableLandmarkPlacement(self, landmark_name):
        # Check if this is the spline landmark
        if landmark_name == "Annulus Contour (Spline)":
            # Create or get spline markups node
            spline_node_name = "Annulus"
            self.logic.spline_node = slicer.mrmlScene.GetFirstNodeByName(spline_node_name)
            
            if not self.logic.spline_node:
                # Create new spline node
                self.logic.spline_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsClosedCurveNode")
                self.logic.spline_node.SetName(spline_node_name)
                # Set spline properties
                self.logic.spline_node.SetCurveTypeToCardinalSpline()
                self.logic.spline_node.GetDisplayNode().SetSelectedColor(1, 1, 0)  # Yellow
                self.logic.spline_node.GetDisplayNode().SetLineWidth(3)
            
            # Enable placement mode for spline
            placeWidget = slicer.qSlicerMarkupsPlaceWidget()
            placeWidget.setMRMLScene(slicer.mrmlScene)
            placeWidget.setCurrentNode(self.logic.spline_node)
            placeWidget.setPlaceModeEnabled(True)
            
            # Setup observer for spline
            self.logic.setupSplineObserver()
            
        else:
            # Original code for point landmarks
            if not hasattr(self.logic, 'markups_node') or not self.logic.markups_node:
                self.logic.markups_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
                self.logic.markups_node.SetName(f"Landmarks_{self.logic.current_case_name}")
                slicer.app.processEvents()
            
            # Check if landmark already exists
            landmark_exists = False
            if hasattr(self.logic, 'markups_node') and self.logic.markups_node:
                num_points = self.logic.markups_node.GetNumberOfControlPoints()
                for i in range(num_points):
                    point_label = self.logic.markups_node.GetNthControlPointLabel(i)
                    if landmark_name in point_label:
                        landmark_exists = True
                        break
            
            if not landmark_exists:
                # Enable placement mode for new landmark
                placeWidget = slicer.qSlicerMarkupsPlaceWidget()
                placeWidget.setMRMLScene(slicer.mrmlScene)
                originalName = self.logic.markups_node.GetName()
                self.logic.markups_node.SetName(f"{landmark_name} ")
                placeWidget.setCurrentNode(self.logic.markups_node)
                placeWidget.setPlaceModeEnabled(True)

                # Restore name after short delay (after placement will start)
                qt.QTimer.singleShot(500, lambda: self.logic.markups_node.SetName(originalName))

                self.logic.setupActivityObserver("landmark")

    def onSaveCaseClicked(self):
        """Handle save case button click"""
        if hasattr(self.logic, 'current_case_name'):
            case_name = self.logic.current_case_name
            save_path = os.path.join(self.logic.main_folder, case_name, 'Platipy', f'landmarks_{case_name}.mrk.json')
            
            if os.path.exists(save_path):
                reply = qt.QMessageBox.question(None, "Overwrite Existing", 
                                            f"Landmarks file already exists for {case_name}. Overwrite?",
                                            qt.QMessageBox.Yes | qt.QMessageBox.No)
                if reply != qt.QMessageBox.Yes:
                    return
            
            self.logic.saveLandmarks()
            qt.QMessageBox.information(None, "Saved", f"Case {case_name} saved successfully!")

    def onLandmarkItemClicked(self, item):
        """Handle clicking on a landmark in the progress list"""
        item_text = item.text()
        landmark_name = item_text.split(":")[0].strip()
        
        # Auto-lock previous landmark if it was unlocked
        if hasattr(self, 'selected_landmark') and self.selected_landmark != landmark_name:
            if self.logic.landmarkExists(self.selected_landmark) and not self.logic.isLandmarkLocked(self.selected_landmark):
                self.logic.lockUnlockLandmark(self.selected_landmark, lock=True)
                self._logActivity("landmark", self.selected_landmark, "Auto-locked")
        # Clear previous current_landmark
        self.logic.current_landmark = None
        
        # Store selected landmark
        self.selected_landmark = landmark_name
        
        # Visual feedback for selection
        self.landmarkProgressList.setCurrentItem(item)
        
        # Enable placement mode if landmark exists and is unlocked, or doesn't exist yet
        exists = self.logic.landmarkExists(landmark_name)
        if not exists or (exists and not self.logic.isLandmarkLocked(landmark_name)):
            # Set current landmark in logic for proper labeling
            self.logic.current_landmark = landmark_name
            self.enableLandmarkPlacement(landmark_name)
            action = "Edit" if exists else "Place"
            self._logActivity("landmark", landmark_name, f"Started {action.lower()}ing")
        
        # Update action buttons
        self.updateActionButtons(landmark_name)
        self.updateLandmarkProgressList()  # Refresh to show auto-lock changes
        
        print(f"Selected landmark: {landmark_name}")

    def updateActionButtons(self, landmark_name):
        """Update button states based on selected landmark"""
        if not landmark_name:
            self.lockUnlockButton.setEnabled(False)
            return
        
        # Check if landmark exists
        exists = self.logic.landmarkExists(landmark_name)
        
        if exists:
            is_locked = self.logic.isLandmarkLocked(landmark_name)
            if is_locked:
                self.lockUnlockButton.setText("Click to Unlock Landmark")
                self.lockUnlockButton.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; }")  # Red for locked
            else:
                self.lockUnlockButton.setText("Click to Lock Landmark")
                self.lockUnlockButton.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }")  # Green for unlocked
            self.lockUnlockButton.setEnabled(True)
            self.resetLandmarkButton.setEnabled(not is_locked)
        else:
            self.lockUnlockButton.setText("-")
            self.lockUnlockButton.setStyleSheet("QPushButton { background-color: #9E9E9E; color: white; font-weight: bold; }")  # Gray for disabled
            self.lockUnlockButton.setEnabled(False)
            self.resetLandmarkButton.setEnabled(False)

    def onCaseListItemActivated(self, item):
        """Handles double-click or Enter key on case list item"""
        self.onSelectCase()

    def onLockUnlockClicked(self):
        """Toggle lock state of selected landmark"""
        if not hasattr(self, 'selected_landmark'):
            return
        
        landmark_name = self.selected_landmark
        is_locked = self.logic.isLandmarkLocked(landmark_name)
        
        # Toggle lock state
        self.logic.lockUnlockLandmark(landmark_name, lock=not is_locked)
        
        # Update UI
        self.updateActionButtons(landmark_name)
        self.updateLandmarkProgressList()
        
        # Log activity
        action = "Locked" if not is_locked else "Unlocked"
        self._logActivity("landmark", landmark_name, action)

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

        # Check if current work needs saving before switching
        if hasattr(self, 'markups_node') and self.markups_node and hasattr(self, 'current_case_name'):
            num_points = self.markups_node.GetNumberOfControlPoints()
            if num_points > 0:
                # There are unsaved landmarks - prompt user
                reply = qt.QMessageBox.question(None, "Unsaved Work", 
                                            f"You have unsaved landmarks for {self.current_case_name}. Save before switching?",
                                            qt.QMessageBox.Yes | qt.QMessageBox.No | qt.QMessageBox.Cancel)
                if reply == qt.QMessageBox.Yes:
                    self.saveLandmarks()  # We'll need to implement this
                elif reply == qt.QMessageBox.Cancel:
                    return  # Don't switch cases
                # If No, continue without saving
        
        # Clear the scene when switching cases
        slicer.mrmlScene.Clear(0)

        # Clear selected landmark when switching cases
        if hasattr(self, 'widget_reference'):
            if hasattr(self.widget_reference, 'selected_landmark'):
                delattr(self.widget_reference, 'selected_landmark')

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


        # view setup and window/level
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)       
        volumeNode = slicer.util.loadVolume(case_path)            
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
        displayNode = volumeNode.GetDisplayNode()
        displayNode.SetAutoWindowLevel(False)  # Turn off auto mode first
        displayNode.SetWindow(2000)
        displayNode.SetLevel(500)

        # Create markups node for this case if it doesn't exist
        node_name = f"Landmarks_{case_name}"
        landmarks_path = os.path.join(self.main_folder, case_name, 'Platipy', f'landmarks_{case_name}.mrk.json')
    
        if os.path.exists(landmarks_path):
            self.markups_node = slicer.util.loadMarkups(landmarks_path)
            self.markups_node.SetName(node_name)
            print(f"Loaded existing point landmarks from: {landmarks_path}")
        else:
            self.markups_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLMarkupsFiducialNode")
            self.markups_node.SetName(node_name)
            print(f"Created new landmarks node: {node_name}")
        
        # Load existing spline - find any spline node and rename it
        spline_node = slicer.mrmlScene.GetFirstNodeByClass("vtkMRMLMarkupsClosedCurveNode")
        if spline_node:
            spline_node.SetName("Annulus")
            self.spline_node = spline_node
            spline_points = spline_node.GetNumberOfControlPoints()
            print(f"Found and renamed spline with {spline_points} points")
        else:
            self.spline_node = None
            print("No existing spline found")

        self.current_case_name = case_name
        self.checkForIncompleteWork() # in case of a previous abrupt exit

        # Reset button states
        if hasattr(self, 'widget_reference'):
            self.widget_reference.lockUnlockButton.setEnabled(False)
            self.widget_reference.markCompleteButton.setEnabled(False)
            self.widget_reference.resetLandmarkButton.setEnabled(False)       
        
        self.widget_reference.saveCaseButton.show() # to show save case button

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
        """Return progress dictionary with compact status for each landmark type"""
        landmark_types = [
            "Left Coronary Cusp Nadir",
            "Right Coronary Cusp Nadir", 
            "Non Coronary Cusp Nadir",
            "Right-Left Commissure",
            "Right-Non Commissure",
            "Left-Non Commissure",
            "Left Coronary Ostium Base",
            "Right Coronary Ostium Base",
            "Annulus Contour (Spline)"
        ]
        
        progress = {}
        
        # Check point landmarks
        if hasattr(self, 'markups_node') and self.markups_node:
            placed_landmarks = []
            num_points = self.markups_node.GetNumberOfControlPoints()
            for i in range(num_points):
                point_label = self.markups_node.GetNthControlPointLabel(i)
                placed_landmarks.append(point_label)
            
            # Set status for point landmarks
            for landmark in landmark_types[:-1]:  # All except spline
                if landmark in placed_landmarks:
                    progress[landmark] = "✓"
                else:
                    progress[landmark] = "✗"
        else:
            # No markups node - all point landmarks not placed
            for landmark in landmark_types[:-1]:
                progress[landmark] = "✗"
        
        # Check spline landmark separately
        if hasattr(self, 'spline_node') and self.spline_node:
            spline_points = self.spline_node.GetNumberOfControlPoints()
            if spline_points >= 3:  # Minimum for a meaningful contour
                progress["Annulus Contour (Spline)"] = f"✓ ({spline_points} pts)"
            elif spline_points > 0:
                progress["Annulus Contour (Spline)"] = f"⚠ ({spline_points} pts)"
            else:
                progress["Annulus Contour (Spline)"] = "✗"
        else:
            progress["Annulus Contour (Spline)"] = "✗"
        
        return progress

    def setupActivityObserver(self, activity_type):
        """Set up observer to detect when activities (landmarks/segments) are placed"""
        if hasattr(self, 'markups_node') and self.markups_node:
            # Remove existing observer if any
            if hasattr(self, 'observer_tag'):
                self.markups_node.RemoveObserver(self.observer_tag)
            
            # Add observer for point additions
            self.observer_tag = self.markups_node.AddObserver(
                self.markups_node.PointPositionDefinedEvent, 
                lambda caller, event: self.onActivityPlaced(caller, event, activity_type)
            )

    def onActivityPlaced(self, caller, event, activity_type):
        """Called when an activity (landmark/segment) is placed"""
        num_points = self.markups_node.GetNumberOfControlPoints()
        if num_points > 0:
            # Get the last placed point
            point_index = num_points - 1
            pos = [0, 0, 0]
            self.markups_node.GetNthControlPointPosition(point_index, pos)
            
            # Set the point label to match the landmark name            
            if activity_type == "landmark":
                activity_name = getattr(self, 'current_landmark', 'Unknown')
                self.markups_node.SetNthControlPointLabel(point_index, activity_name)
            
            # Log the placement
            if hasattr(self, 'current_log_manager') and self.current_log_manager:
                activity_name = getattr(self, 'current_landmark', 'Unknown')
                self.current_log_manager.write_entry(
                    f"Placed {activity_type}: {activity_name}"
                )     
                            
            # Update UI after placement
            if hasattr(self, 'widget_reference'):
                self.widget_reference.updateActionButtons(activity_name)
                self.widget_reference.updateLandmarkProgressList()     

    def lockUnlockLandmark(self, landmark_name, lock=True):
        """Lock or unlock points of the current landmark type"""
        if landmark_name == "Annulus Contour (Spline)":
            self.lockUnlockSpline(lock)
        else:
            # Original code for point landmarks
            if hasattr(self, 'markups_node') and self.markups_node:
                num_points = self.markups_node.GetNumberOfControlPoints()
                for i in range(num_points):
                    point_label = self.markups_node.GetNthControlPointLabel(i)
                    if landmark_name in point_label:
                        self.markups_node.SetNthControlPointLocked(i, lock)

    def checkForIncompleteWork(self):
        """Check if there was incomplete work and warn user"""
        incomplete_items = []
        
        # Check point landmarks
        if hasattr(self, 'markups_node') and self.markups_node:
            num_points = self.markups_node.GetNumberOfControlPoints()
            for i in range(num_points):
                if not self.markups_node.GetNthControlPointLocked(i):
                    point_label = self.markups_node.GetNthControlPointLabel(i)
                    incomplete_items.append(f"Point: {point_label}")
        
        # Check spline
        if hasattr(self, 'spline_node') and self.spline_node:
            spline_points = self.spline_node.GetNumberOfControlPoints()
            spline_locked = True
            
            for i in range(spline_points):
                if not self.spline_node.GetNthControlPointLocked(i):
                    spline_locked = False
                    break
            
            if not spline_locked and spline_points > 0:
                incomplete_items.append(f"Spline: Annulus Contour ({spline_points} points)")
        
        if incomplete_items:
            items_text = "\n".join(incomplete_items)
            qt.QMessageBox.warning(None, "Incomplete Work Detected", 
                                f"Warning: Found unlocked landmarks from previous session:\n{items_text}\n\nPlease review and complete or reset these landmarks.")
            
            # Log the warning
            if hasattr(self, 'current_log_manager') and self.current_log_manager:
                self.current_log_manager.write_entry(f"Warning: Incomplete work detected: {', '.join(incomplete_items)}")

    def saveLandmarks(self):
        """Save current landmarks and spline to same JSON file"""
        if hasattr(self, 'current_case_name'):
            save_path = os.path.join(self.main_folder, self.current_case_name, 'Platipy', f'landmarks_{self.current_case_name}.mrk.json')
            
            # First save the landmarks
            if hasattr(self, 'markups_node') and self.markups_node:
                slicer.util.saveNode(self.markups_node, save_path)
            
            # Then manually add spline data to the JSON file
            if hasattr(self, 'spline_node') and self.spline_node and os.path.exists(save_path):
                import json
                
                # Read existing JSON
                with open(save_path, 'r') as f:
                    data = json.load(f)
                
                # Save spline to temp file to get its JSON structure
                temp_path = save_path.replace('.mrk.json', '_temp.mrk.json')
                slicer.util.saveNode(self.spline_node, temp_path)
                
                # Read spline JSON
                with open(temp_path, 'r') as f:
                    spline_data = json.load(f)
                
                # Add spline markups to main file
                if 'markups' in spline_data:
                    data['markups'].extend(spline_data['markups'])
                
                # Write combined data
                with open(save_path, 'w') as f:
                    json.dump(data, f, indent=2)
                
                # Clean up temp file
                os.remove(temp_path)
            
            print(f"All landmarks saved to: {save_path}")

    def setupSplineObserver(self):
        """Set up observer specifically for spline landmark"""
        if hasattr(self, 'spline_node') and self.spline_node:
            # Remove existing observer if any
            if hasattr(self, 'spline_observer_tag'):
                self.spline_node.RemoveObserver(self.spline_observer_tag)
            
            # Add observer for point additions to spline
            self.spline_observer_tag = self.spline_node.AddObserver(
                self.spline_node.PointPositionDefinedEvent, 
                self.onSplinePointPlaced
            )

    def onSplinePointPlaced(self, caller, event):
        """Called when a point is added to the spline"""
        num_points = self.spline_node.GetNumberOfControlPoints()
        if num_points > 0:
            # Get the last placed point
            point_index = num_points - 1
            pos = [0, 0, 0]
            self.spline_node.GetNthControlPointPosition(point_index, pos)
            
            # Log the spline point placement
            if hasattr(self, 'current_log_manager') and self.current_log_manager:
                self.current_log_manager.write_entry(
                    f"Added spline point {point_index + 1} at position ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})"
                )
            
            # Update progress display
            if hasattr(self, 'widget_reference'):
                self.widget_reference.updateLandmarkProgressList()
                self.widget_reference.updateActionButtons("Annulus Contour (Spline)")

    def lockUnlockSpline(self, lock=True):
        """Lock or unlock the spline node"""
        if hasattr(self, 'spline_node') and self.spline_node:
            num_points = self.spline_node.GetNumberOfControlPoints()
            for i in range(num_points):
                self.spline_node.SetNthControlPointLocked(i, lock)

    def resetSpline(self):
        """Reset/clear the current spline"""
        if hasattr(self, 'spline_node') and self.spline_node:
            # Clear all control points
            self.spline_node.RemoveAllControlPoints()
            
            # Log the reset
            if hasattr(self, 'current_log_manager') and self.current_log_manager:
                self.current_log_manager.write_entry("Reset Annulus Contour (Spline)")

    def landmarkExists(self, landmark_name):
        """Check if a landmark has been placed"""
        if landmark_name == "Annulus Contour (Spline)":
            return hasattr(self, 'spline_node') and self.spline_node and self.spline_node.GetNumberOfControlPoints() > 0
        else:
            if hasattr(self, 'markups_node') and self.markups_node:
                num_points = self.markups_node.GetNumberOfControlPoints()
                for i in range(num_points):
                    point_label = self.markups_node.GetNthControlPointLabel(i)
                    if landmark_name in point_label:
                        return True
            return False

    def isLandmarkLocked(self, landmark_name):
        """Check if a landmark is locked"""
        if landmark_name == "Annulus Contour (Spline)":
            if hasattr(self, 'spline_node') and self.spline_node:
                num_points = self.spline_node.GetNumberOfControlPoints()
                if num_points > 0:
                    return self.spline_node.GetNthControlPointLocked(0)  # Check first point
            return False
        else:
            if hasattr(self, 'markups_node') and self.markups_node:
                num_points = self.markups_node.GetNumberOfControlPoints()
                for i in range(num_points):
                    point_label = self.markups_node.GetNthControlPointLabel(i)
                    if landmark_name in point_label:
                        return self.markups_node.GetNthControlPointLocked(i)
            return False


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