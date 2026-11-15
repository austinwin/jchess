# Coach Hoang

Coach Hoang is an automated educational chess tutor, not a human chess master. Its goal is to help students improve through personalized, validated practice.

## Student workflow
The Coach Hoang tab creates a six-exercise practice session drawn from JChess's existing legally checked puzzles. Each session emphasizes tactics, king and piece safety, strategic planning, endgames and calculation. The coach examines up to 60 recent puzzle attempts and suggests a possible weaker category only after at least three attempts in that category. Small samples are treated as inconclusive.

Students can start each exercise on the chessboard, request non-spoiler hints before solving (free), and request a deeper explanation after solving or receiving a parent-approved reveal. The optional AI API writes friendly explanations, not chess answer keys. Stockfish remains responsible for actual chess calculation and free-play moves.

## Parent consent and budget
Sign in as a parent, open AI coach, enter a valid OpenAI API key, enable AI features, and separately opt in to Coach Hoang. Choose a daily limit of 1 to 50 AI requests (UI presets 1, 3, 5, 10, 20, 50). Saving the key by itself does not enable the child-facing feature. Parents can disable AI or remove the encrypted key.

JChess stores encrypted keys in the database, and keeps the encryption secret separately in Render configuration. The coach_access table enforces daily usage with a database lock. Each attempted API call counts, even if the provider fails. This is not a monetary cost ceiling; use the OpenAI project billing controls too.

## Data and answers
For training plans, OpenAI receives aggregated category statistics and metadata about selected themes. For completed exercise explanations, it receives the specific chess FEN, teaching notes and attempted moves. No child names, logins, session tokens, API secrets, full game history or hidden puzzle solutions are sent. Requests set store=false. AI output is structured as three short, length-limited explanations and validated on the server. There is no unrestricted chat.

The latest training plan is saved under coach_plans for the student and linked parents to revisit. The server chooses exercises from the validated library before calling AI.

## Current limitations
The system assembles personalized training sessions from verified puzzles; it does not yet create brand-new original engine-checked tactical positions. Practice bands and weaknesses are approximations, not certified chess ratings or tournament predictions. AI advice may be imperfect. These tools support consistent practice but cannot promise competition results.
