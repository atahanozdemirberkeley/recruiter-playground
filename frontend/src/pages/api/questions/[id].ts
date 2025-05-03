import type { NextApiRequest, NextApiResponse } from 'next';

type QuestionData = {
  id: string;
  title: string;
  description: string;
  difficulty: string;
  category: string;
  // Add any other fields that your question might have
};

type ErrorResponse = {
  error: string;
};

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse<QuestionData | ErrorResponse>
) {
  const { id } = req.query;

  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // This URL should be configured in your environment variables
    const backendUrl = process.env.BACKEND_API_URL || 'http://localhost:8000';
    
    // Make a request to your backend API
    const response = await fetch(`${backendUrl}/api/questions/${id}`);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error(`Backend API error: ${errorText}`);
      return res.status(response.status).json({ 
        error: `Failed to fetch question data: ${response.statusText}` 
      });
    }
    
    const questionData = await response.json();
    
    // Return the question data
    return res.status(200).json(questionData);
  } catch (error) {
    console.error('Error fetching question data:', error);
    return res.status(500).json({ 
      error: 'Internal server error while fetching question data' 
    });
  }
} 