# Overview

This is a comprehensive medical record management system specifically designed for Luna Princess Mendes Guimarães, a pet dog. The system provides a digital medical chart (prontuário) that allows medical teams to access and review laboratory test results, clinical history, medications, and media files. The application features both public viewing capabilities and secure administrative functions for data management.

The system processes medical documents using AI-powered text extraction and creates visualizations including interactive charts, timelines, and comparison tools. It's built as a web application using Python with a focus on creating an impressive, user-friendly interface with a "pediatric" pink theme suitable for a female dog patient.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Framework**: Streamlit-based web application for rapid development and interactive dashboards
- **UI Components**: Modular component system with separate classes for lab results, timeline, and comparison views
- **Styling**: Custom CSS with pink/pediatric theme, responsive design for desktop and mobile
- **Navigation**: Tab-based interface with public viewing and admin-only sections accessed via `/admin` route
- **Charts**: Plotly integration for interactive graphs, timelines, and data visualizations

## Backend Architecture
- **Language**: Python-based backend with object-oriented design patterns
- **Database Layer**: PostgreSQL with direct psycopg2 connections, managed through DatabaseManager class
- **Authentication**: Custom authentication system using bcrypt for password hashing and session management
- **File Processing**: AI-powered document processing using OpenAI API for PDF text extraction and data interpretation
- **Data Management**: Structured storage for lab results, medical timeline events, medications, and user information

## Data Storage Solutions
- **Primary Database**: PostgreSQL with tables for users, patients, lab results, medical timeline, and medications
- **File Storage**: Internal file system storage for uploaded PDFs and media files
- **Configuration**: Environment-based configuration using PostgreSQL connection parameters
- **Data Structure**: Normalized database schema with proper foreign key relationships between entities

## Authentication and Authorization
- **User Management**: Email/password authentication with bcrypt password hashing
- **Session Management**: Streamlit session state for maintaining user authentication
- **Access Control**: Two-tier access system - public read-only access and admin-only editing capabilities
- **Security**: Protected admin routes requiring authentication, with user session validation

## External Dependencies
- **AI Processing**: OpenAI API integration for intelligent document processing and text extraction
- **PDF Processing**: PyPDF2 and pdfplumber libraries for extracting text from medical documents
- **Data Visualization**: Plotly for creating interactive charts and graphs
- **Database**: PostgreSQL as the primary database system
- **File Handling**: PIL (Python Imaging Library) for image processing
- **Data Processing**: Pandas for data manipulation and analysis
- **Web Framework**: Streamlit for the web interface and user interactions

# External Dependencies

## Third-party Services
- **OpenAI API**: Used for AI-powered processing of medical documents, text extraction, and intelligent data interpretation
- **PostgreSQL Database**: Primary data storage for all application data including user accounts, lab results, and medical records

## Python Libraries
- **Streamlit**: Web application framework for creating the interactive dashboard
- **PyPDF2 & pdfplumber**: PDF text extraction and processing
- **Plotly**: Interactive data visualization and charting
- **psycopg2**: PostgreSQL database connectivity
- **bcrypt**: Password hashing and authentication security
- **Pandas**: Data manipulation and analysis
- **PIL (Pillow)**: Image processing and handling
- **NumPy**: Numerical computations and data processing

## Integration Points
- **File Upload System**: Handles PDF documents, images, audio, and video files for processing
- **Unit Conversion System**: Automatic conversion between different laboratory measurement units
- **Export Functionality**: Data export capabilities for charts, tables, and medical reports
- **Mobile Responsiveness**: Progressive Web App features for mobile device compatibility