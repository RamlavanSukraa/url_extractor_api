##########################################################
#                                                        #
#  Auth:       Sukraa Software Solutions                 #
#  Created:    11/13/2024                                #
#  Project:    Prescription AI Agent                     #          
#                                                        #
#  Summary:    This project facilitates the extraction,  #
#              mapping, and storage of prescription      #
#              data using MongoDB. It supports image     #
#              processing from both local and external   #
#              URLs, converting image data into          #
#              structured information with AI Agent      #
#                                                        #
##########################################################                                                        
                                                        

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware 
from routes.url_api import router as url_router


app = FastAPI()


allowed_origins = [
    
    "http://localhost:3001",
    "http://localhost:3002",
    "http://localhost:3003"

]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include the router
app.include_router(url_router)




