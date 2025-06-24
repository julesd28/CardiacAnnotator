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

    # Create logic instance
    self.logic = CardiacAnnotatorLogic()
    
    
    # Directory selector
    self.loadCasesButton = qt.QPushButton("Load cases")
    self.layout.addWidget(self.loadCasesButton)
    
    # Connect signal
    self.layout.addWidget(self.loadCasesButton)
    self.loadCasesButton.connect('clicked()', self.onLoadCasesClicked)
    self.layout.addStretch(1)  

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

class CardiacAnnotatorLogic(ScriptedLoadableModuleLogic):

  def initializeProgressTracking(self, main_folder):
    self.main_folder = main_folder
    self.csv_path = os.path.join(main_folder, "progress_tracking.csv")
    
    # Load or create CSV
    if os.path.exists(self.csv_path):
        self.progress_df = pd.read_csv(self.csv_path)
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





class CardiacAnnotatorTest(ScriptedLoadableModuleTest):
  def runTest(self):
    pass