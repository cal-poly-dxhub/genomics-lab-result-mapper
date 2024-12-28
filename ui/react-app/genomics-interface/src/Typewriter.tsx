// src/Typewriter.tsx
import React, { useState, useEffect } from "react";

interface TypewriterProps {
  words: string[];          // Array of words to display
  typingSpeed?: number;     // Speed of typing in milliseconds
  deletingSpeed?: number;   // Speed of deleting in milliseconds
  pauseTime?: number;       // Time to pause before deleting
}

const Typewriter: React.FC<TypewriterProps> = ({
  words,
  typingSpeed = 150,
  deletingSpeed = 100,
  pauseTime = 2000,
}) => {
  const [currentWordIndex, setCurrentWordIndex] = useState<number>(0);
  const [displayedText, setDisplayedText] = useState<string>("");
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [isPaused, setIsPaused] = useState<boolean>(false);

  useEffect(() => {
    const currentWord = words[currentWordIndex];
    let timer: ReturnType<typeof setTimeout>; // Use ReturnType to infer the correct type

    if (isPaused) {
      timer = setTimeout(() => {
        setIsPaused(false);
        setIsDeleting(true);
      }, pauseTime);
    } else if (isDeleting) {
      timer = setTimeout(() => {
        setDisplayedText(currentWord.substring(0, displayedText.length - 1));
        if (displayedText.length - 1 === 0) {
          setIsDeleting(false);
          setCurrentWordIndex((prev) => (prev + 1) % words.length);
        }
      }, deletingSpeed);
    } else {
      timer = setTimeout(() => {
        setDisplayedText(currentWord.substring(0, displayedText.length + 1));
        if (displayedText.length + 1 === currentWord.length) {
          // If it's the last word, don't delete
          if (currentWordIndex === words.length - 1) {
            // Do nothing, persist the last word
            return;
          }
          setIsPaused(true);
        }
      }, typingSpeed);
    }

    return () => clearTimeout(timer);
  }, [displayedText, isDeleting, isPaused, words, currentWordIndex, typingSpeed, deletingSpeed, pauseTime]);

  return (
    <>
      <span className="title-shadow">{displayedText}</span>
      {/* Optional: Blinking Cursor */}
      {/* Uncomment the following lines if you want to include a blinking cursor */}
      {/* {!(currentWordIndex === words.length - 1 && displayedText === words[currentWordIndex]) && (
        <span className="typewriter-cursor" aria-hidden="true"></span>
      )} */}
    </>
  );
};

export default Typewriter;
