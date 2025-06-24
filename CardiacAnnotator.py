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

        # Case Navigator Section    
        landmarkCollapsibleButton = ctk.ctkCollapsibleButton()
        landmarkCollapsibleButton.text = "Case Navigator"
        self.layout.addWidget(landmarkCollapsibleButton)

        navigatorLayout = qt.QVBoxLayout(landmarkCollapsibleButton)
        self.loadCasesButton = qt.QPushButton("Load cases folder")
        navigatorLayout.addWidget(self.loadCasesButton)

        # Show active case
        self.activeCaseLabel = qt.QLabel("Active case:")
        self.activeCaseLabel.hide()  
        navigatorLayout.addWidget(self.activeCaseLabel)
        self.activeCaseWidget = qt.QLabel()
        self.activeCaseWidget.setAlignment(qt.Qt.AlignCenter)
        self.activeCaseWidget.setMaximumHeight(20)
        self.activeCaseWidget.setStyleSheet("border: 1px solid gray;font-weight: bold;")
        self.activeCaseWidget.hide()
        navigatorLayout.addWidget(self.activeCaseWidget) 

        # Add case list widget
        self.caseLabel = qt.QLabel("Next cases:")
        self.caseLabel.hide()  
        navigatorLayout.addWidget(self.caseLabel)
        
        # Create horizontal layout for list and button
        caseLayout = qt.QHBoxLayout()
        
        # Add list on the left
        self.caseListWidget = qt.QListWidget()
        self.caseListWidget.setMaximumHeight(100)
        self.caseListWidget.hide()
        self.caseListWidget.setVerticalScrollBarPolicy(qt.Qt.ScrollBarAsNeeded)
        caseLayout.addWidget(self.caseListWidget)
        
        # Add button on the right
        self.selectCaseButton = qt.QPushButton("Select Case")
        self.selectCaseButton.hide()
        self.selectCaseButton.setMaximumWidth(100)
        caseLayout.addWidget(self.selectCaseButton)
        
        # Add the horizontal layout to the main layout
        navigatorLayout.addLayout(caseLayout)
        
        self.selectCaseButton.connect('clicked()', self.onSelectCase)

        # Connect signal
        self.loadCasesButton.connect('clicked()', self.onLoadCasesClicked)
        self.layout.addStretch(1)


    def updateCaseList(self, next_cases):
        self.caseLabel.show()
        self.caseListWidget.clear()
        
        for case in next_cases[:5]:
            # Check if case is in progress
            case_row = self.logic.progress_df[self.logic.progress_df['Case_ID'] == case]
            if not case_row.empty and case_row.iloc[0]['Status'] == 'in_progress':
                display_text = f"{case} (in progress)"
            else:
                display_text = case
                
            self.caseListWidget.addItem(display_text)
        
        self.caseListWidget.show()
        self.selectCaseButton.show()
        self.activeCaseLabel.show() 


    def onSelectCase(self):
        selected_item = self.caseListWidget.currentItem()
        if selected_item:
            display_text = selected_item.text()
            # Remove "(in progress)" if present
            case_name = display_text.replace(" (in progress)", "")
            print(f"Starting work on: {case_name}")
            self.logic.loadCase(case_name)
            # self.activeCaseWidget.clear()
            # self.activeCaseWidget.addItem(case_name)
            self.activeCaseWidget.setText(case_name)
            self.activeCaseWidget.show()


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
            next_cases = self.logic.getNextCases(5)  # You'll need this method in Logic
            self.updateCaseList(next_cases)
            self.activeCaseWidget.show()
            

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

    def startLandmarkTimer(self, landmark_name):
        self.current_landmark = landmark_name
        self.landmark_start_time = time.time()

    def stopLandmarkTimer(self):
        if hasattr(self, 'landmark_start_time'):
            elapsed = time.time() - self.landmark_start_time
            # Update CSV with elapsed time for current landmark
            self.updateLandmarkTime(self.current_landmark, elapsed)


    def getNextCases(self, count):
        if not hasattr(self, 'progress_df'):
            return []
        
        # Get in_progress cases first, then not_started
        in_progress = self.progress_df[self.progress_df['Status'] == 'in_progress']['Case_ID'].tolist()
        not_started = self.progress_df[self.progress_df['Status'] == 'not_started']['Case_ID'].tolist()
        
        # Combine: in_progress first, then not_started
        pending_cases = in_progress + not_started
        
        return pending_cases[:count]


    
    def loadCase(self, case_name):  
        # Find the file path for this case
        case_path = os.path.join(self.main_folder, case_name, 'Platipy', f'{case_name} 40pc.nii.gz')
        # Load in Slicer
        slicer.util.loadVolume(case_path)
        # Update status
        self.updateCaseStatus(case_name, "in_progress")
        # Set four-up view
        slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)




class CardiacAnnotatorTest(ScriptedLoadableModuleTest):
  def runTest(self):
    pass